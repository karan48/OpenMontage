"""Contract tests for channel profiles (channels/<id>/): every profile validates
and resolves its references, the loader rejects broken ones, and init_project
records the channel in project.json."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from lib.channel_profile import (
    CHANNELS_DIR,
    ChannelProfileError,
    brand_intro,
    list_channels,
    load_channel,
    resolve_format,
    validate_channel,
)
from lib.checkpoint import PROJECT_MARKER_FILENAME, init_project
from styles.playbook_loader import load_playbook, validate_accessibility

TEMPLATE_DIR = CHANNELS_DIR / "_template"


def _template_copy(tmp_path, channel_id="test-channel") -> tuple:
    """Copy the template into tmp_path/<channel_id> and return (dir, profile)."""
    folder = tmp_path / channel_id
    shutil.copytree(TEMPLATE_DIR, folder)
    with open(folder / "channel.yaml", encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    profile["id"] = channel_id
    return folder, profile


def _write(folder, profile) -> None:
    with open(folder / "channel.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(profile, f, allow_unicode=True)


class TestShippedChannels:
    def test_channels_exist(self):
        assert list_channels(), "channels/ should hold at least one profile"

    @pytest.mark.parametrize("channel_id", list_channels())
    def test_channel_loads_and_resolves(self, channel_id):
        profile = load_channel(channel_id)
        assert profile["id"] == channel_id

    @pytest.mark.parametrize("channel_id", list_channels())
    def test_channel_makes_long_form_and_shorts(self, channel_id):
        formats = load_channel(channel_id)["formats"]
        assert set(formats) == {"long_form", "shorts"}
        assert formats["long_form"]["aspect_ratio"] == "16:9"
        assert formats["shorts"]["aspect_ratio"] == "9:16"

    @pytest.mark.parametrize("channel_id", list_channels())
    def test_script_guide_covers_both_formats(self, channel_id):
        guide = (CHANNELS_DIR / channel_id / "script-guide.md").read_text(encoding="utf-8")
        assert "## Long-form structure" in guide
        assert "## Shorts structure" in guide

    @pytest.mark.parametrize("channel_id", list_channels())
    def test_channel_playbook_is_accessible(self, channel_id):
        playbook = load_playbook(load_channel(channel_id)["production"]["style_playbook"])
        report = validate_accessibility(playbook)
        assert report["pass"], report["issues"]

    def test_template_validates(self):
        with open(TEMPLATE_DIR / "channel.yaml", encoding="utf-8") as f:
            validate_channel(yaml.safe_load(f), TEMPLATE_DIR)

    def test_template_is_not_listed(self):
        assert "_template" not in list_channels()


class TestLoaderRejectsBrokenProfiles:
    def test_unknown_channel(self, tmp_path):
        with pytest.raises(ChannelProfileError, match="Channel not found"):
            load_channel("nope", channels_dir=tmp_path)

    def test_id_must_match_folder(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["id"] = "other-name"
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="must match the folder name"):
            load_channel("test-channel", channels_dir=tmp_path)

    def test_unknown_playbook(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["production"]["style_playbook"] = "no-such-playbook"
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="Playbook not found"):
            load_channel("test-channel", channels_dir=tmp_path)

    def test_unknown_pipeline(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["production"]["alternate_pipelines"] = {"x": "no-such-pipeline"}
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="no-such-pipeline"):
            load_channel("test-channel", channels_dir=tmp_path)

    def test_unknown_media_profile(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["formats"]["shorts"]["media_profile"] = "vhs_tape"
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="formats.shorts.media_profile"):
            load_channel("test-channel", channels_dir=tmp_path)

    def test_unknown_format_pipeline_override(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["formats"]["long_form"]["pipeline"] = "no-such-pipeline"
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="no-such-pipeline"):
            load_channel("test-channel", channels_dir=tmp_path)

    def test_unknown_format_name_rejected(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["formats"]["podcast"] = profile["formats"]["shorts"]
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="formats"):
            load_channel("test-channel", channels_dir=tmp_path)

    def test_missing_script_guide(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        (folder / "script-guide.md").unlink()
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="script.guide"):
            load_channel("test-channel", channels_dir=tmp_path)

    def test_schema_violation_names_the_field(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["script"]["humor"] = "extreme"
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="script/humor"):
            load_channel("test-channel", channels_dir=tmp_path)

    def test_devanagari_round_trips(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["narration"]["register"] = "मैं आपको बताता हूँ"
        _write(folder, profile)
        assert load_channel("test-channel", channels_dir=tmp_path)["narration"]["register"] == "मैं आपको बताता हूँ"


class TestBrand:
    def test_explainer_intro_resolves(self):
        profile = load_channel("explainer")
        intro = brand_intro(profile, "long_form")
        assert intro is not None and intro["seconds"] == 3.0 and intro["placement"] == "after_promise"
        assert Path(intro["file"]).exists() and Path(intro["audio"]).exists()

    def test_explainer_shorts_use_an_end_bug_not_an_intro(self):
        shorts = brand_intro(load_channel("explainer"), "shorts")
        assert shorts is not None and shorts["mode"] == "end_bug"
        assert Path(shorts["logo"]).exists() and Path(shorts["audio"]).exists()

    def test_brand_is_optional(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        _write(folder, profile)
        loaded = load_channel("test-channel", channels_dir=tmp_path)
        assert "brand" not in loaded
        assert brand_intro(loaded, "long_form", channels_dir=tmp_path) is None

    def test_missing_brand_logo_rejected(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["brand"] = {"logo": "brand/nope.png"}
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="brand.logo"):
            load_channel("test-channel", channels_dir=tmp_path)

    def test_missing_intro_file_rejected(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["brand"] = {"intro": {"long_form": {"file": "brand/intro.mp4", "seconds": 3.0}}}
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="brand.intro.long_form.file"):
            load_channel("test-channel", channels_dir=tmp_path)

    def test_intro_seconds_must_be_positive(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["brand"] = {"intro": {"long_form": {"file": "x.mp4", "seconds": 0}}}
        _write(folder, profile)
        with pytest.raises(ChannelProfileError, match="brand/intro/long_form/seconds"):
            load_channel("test-channel", channels_dir=tmp_path)


class TestResolveFormat:
    def test_inherits_default_pipeline(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        resolved = resolve_format(profile, "shorts")
        assert resolved["pipeline"] == profile["production"]["default_pipeline"]
        assert resolved["aspect_ratio"] == "9:16"

    def test_format_pipeline_override_wins(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        profile["formats"]["long_form"]["pipeline"] = "cinematic"
        assert resolve_format(profile, "long_form")["pipeline"] == "cinematic"

    def test_missing_format_raises(self, tmp_path):
        folder, profile = _template_copy(tmp_path)
        del profile["formats"]["shorts"]
        with pytest.raises(ChannelProfileError, match="no 'shorts' format"):
            resolve_format(profile, "shorts")


class TestInitProjectChannel:
    def test_channel_and_format_written_to_marker(self, tmp_path):
        pdir = init_project(
            "review-short", title="Review", pipeline_type="hybrid",
            pipeline_dir=tmp_path, channel="product-review", video_format="shorts",
        )
        marker = json.loads((pdir / PROJECT_MARKER_FILENAME).read_text())
        assert marker["channel"] == "product-review"
        assert marker["video_format"] == "shorts"

    def test_channel_omitted_when_not_given(self, tmp_path):
        pdir = init_project("p", title="P", pipeline_type="cinematic", pipeline_dir=tmp_path)
        marker = json.loads((pdir / PROJECT_MARKER_FILENAME).read_text())
        assert "channel" not in marker
        assert "video_format" not in marker

    def test_reinit_keeps_channel(self, tmp_path):
        init_project("p", title="P", pipeline_type="cinematic", pipeline_dir=tmp_path, channel="cinematic")
        pdir = init_project("p", title="P2", pipeline_type="cinematic", pipeline_dir=tmp_path)
        marker = json.loads((pdir / PROJECT_MARKER_FILENAME).read_text())
        assert marker["channel"] == "cinematic"
