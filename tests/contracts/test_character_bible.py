"""Contract tests for the character bible (lib/character_bible.py).

Casts and the template validate; prompts are assembled verbatim and
deterministically from the canonical text; reference images are ordered,
filtered and capped by policy; approvals persist with provenance and
detect stale text; scene_plan character_actions feed it directly.
"""

import json

import jsonschema
import pytest
import yaml
from PIL import Image

from lib import character_bible as cb
from lib.channel_profile import CHANNELS_DIR, list_channels, load_channel
from lib.paths import REPO_ROOT
from styles.playbook_loader import load_playbook

TEMPLATE_CAST = CHANNELS_DIR / "_template" / "cast"
EXAMPLE = TEMPLATE_CAST / "_example" / "character.yaml"
STYLE = "3D animated feature film still, warm light"
NO_TEXT = "No text, no letters, no numbers, no signs, no logos, no watermark."

RAJ = {
    "id": "raj",
    "name": "Raj",
    "role": "supporting",
    "status": "draft",
    "identity": {
        "summary": "a 36-year-old Indian man",
        "face": "square face with a short trimmed beard",
        "hair": "short wavy black hair",
        "skin": "medium brown skin",
    },
    "wardrobe": {
        "default": "office",
        "outfits": {"office": {"description": "a light-blue cotton shirt and grey trousers", "short": "light-blue shirt"}},
    },
    "poses": {"arms-crossed": "standing with arms crossed"},
    "expressions": {"angry": "brows drawn together, jaw clenched"},
}


def _example(**overrides):
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data.update(overrides)
    return data


def _write_character(cast_dir, data):
    folder = cast_dir / data["id"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "character.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return folder


def _write_settings(cast_dir, **settings):
    settings.setdefault("style", {"source": "inline", "line": STYLE})
    (cast_dir / "cast.yaml").write_text(yaml.safe_dump(settings), encoding="utf-8")


def _png(path, size=(64, 96), color=(200, 120, 80)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


@pytest.fixture
def cast_dir(tmp_path):
    folder = tmp_path / "cast"
    folder.mkdir()
    _write_settings(folder)
    _write_character(folder, _example(id="meera"))
    _write_character(folder, RAJ)
    return folder


@pytest.fixture
def approve(tmp_path):
    def _approve(cast, character_id, kind, item=None, **kwargs):
        candidate = _png(tmp_path / "candidates" / f"{character_id}-{kind}-{item}.png")
        return cb.approve_ref(cast, character_id, kind, candidate, item=item, **kwargs)

    return _approve


def _load(cast_dir, **kwargs):
    return cb.load_cast_from_dir(cast_dir, **kwargs)


# ---------------------------------------------------------------------------


class TestShippedCasts:
    @pytest.mark.parametrize("channel_id", list_channels())
    def test_every_channel_cast_loads(self, channel_id):
        if not load_channel(channel_id)["visuals"].get("cast_dir"):
            pytest.skip("channel has no structured cast")
        cast = cb.load_cast(channel_id)
        for character_id, report in cb.cast_status(cast).items():
            states = [report["master"], *report["poses"].values(), *report["expressions"].values()]
            assert "stale" not in states, f"{channel_id}/{character_id} has stale references"

    def test_template_example_validates_but_is_skipped_by_default(self):
        playbook = load_playbook("anime-drama")
        assert _load(TEMPLATE_CAST, playbook=playbook).characters == {}
        cast = _load(TEMPLATE_CAST, playbook=playbook, include_underscored=True)
        assert list(cast.characters) == ["example"]
        prefix = playbook["asset_generation"]["image_prompt_prefix"]
        assert cast.style_line == prefix.strip().rstrip(",. ")
        assert cast.settings["models"]["reference"] == "meta/muse-image/edit"

    def test_channel_without_cast_dir_is_reported(self):
        with pytest.raises(cb.CharacterBibleError, match="cast_dir is not set"):
            cb.load_cast("explainer")


class TestLoader:
    def test_id_must_match_folder(self, cast_dir):
        _write_character(cast_dir, _example(id="meera"))
        (cast_dir / "meera").rename(cast_dir / "kamla")
        with pytest.raises(cb.CharacterBibleError, match="must match the folder name"):
            _load(cast_dir)

    def test_default_outfit_must_exist(self, cast_dir):
        bad = _example(id="meera")
        bad["wardrobe"]["default"] = "festive"
        _write_character(cast_dir, bad)
        with pytest.raises(cb.CharacterBibleError, match="wardrobe.default 'festive'"):
            _load(cast_dir)

    def test_schema_error_names_the_field(self, cast_dir):
        bad = _example(id="meera")
        del bad["identity"]["face"]
        _write_character(cast_dir, bad)
        with pytest.raises(cb.CharacterBibleError, match="identity"):
            _load(cast_dir)

    def test_bad_settings_rejected(self, cast_dir):
        _write_settings(cast_dir, reference_policy={"pose_image": "sometimes"})
        with pytest.raises(cb.CharacterBibleError, match="pose_image"):
            _load(cast_dir)

    def test_playbook_style_needs_a_prefix(self, cast_dir):
        _write_settings(cast_dir, style={"source": "playbook"})
        with pytest.raises(cb.CharacterBibleError, match="image_prompt_prefix"):
            _load(cast_dir)

    def test_story_cast_merges_and_ids_are_unique(self, cast_dir, tmp_path):
        story = tmp_path / "project" / "cast"
        _write_character(story, {**RAJ, "id": "kamla", "name": "Kamla"})
        cast = _load(cast_dir, story_dirs=[story])
        assert cast.character("kamla").scope == "story"
        assert cast.character("meera").scope == "channel"

        _write_character(story, RAJ)
        with pytest.raises(cb.CharacterBibleError, match="defined twice"):
            _load(cast_dir, story_dirs=[story])


class TestShots:
    def test_text_shot_pastes_the_identity_verbatim(self, cast_dir):
        cast = _load(cast_dir)
        meera = cast.character("meera")
        req = cb.build_shot(
            cast,
            {"description": "Meera waits at the kitchen door", "characters": [{"id": "meera"}]},
            mode="text",
        )
        assert req["mode"] == "text"
        assert req["prompt"].startswith(STYLE + ", wide 16:9: Meera waits at the kitchen door.")
        assert cb.identity_text(meera) in req["prompt"]
        assert req["prompt"].endswith(NO_TEXT)
        assert (req["width"], req["height"]) == (1344, 768)
        assert req["preferred_provider"] == "flux" and req["image_paths"] == []

    def test_reference_shot_needs_an_approved_master(self, cast_dir):
        cast = _load(cast_dir)
        with pytest.raises(cb.CharacterBibleError, match="no approved master"):
            cb.build_shot(cast, {"description": "x", "characters": [{"id": "meera"}]})

    def test_golden_reference_prompt(self, cast_dir, approve):
        cast = _load(cast_dir)
        master = approve(cast, "meera", "master")
        req = cb.build_shot(
            cast,
            {
                "description": "Meera waits at the kitchen door at dawn",
                "framing": "medium shot",
                "characters": [{"id": "meera", "action": "listens to the argument inside"}],
            },
        )
        assert req["prompt"] == (
            "Image 1 is the character reference for Meera. "
            "Keep Meera's exact face, eyes, eyebrows, skin tone, body proportions, "
            "long black hair in a low bun with a centre parting, a small mole above her upper lip, "
            "a thin gold mangalsutra, a small red bindi and red-and-white bangles and faded green cotton saree. "
            "Ignore the plain backgrounds of the character reference images. "
            "New scene, wide 16:9 medium shot: Meera waits at the kitchen door at dawn. "
            "Meera: listens to the argument inside. "
            f"{STYLE}. {NO_TEXT}"
        )
        assert req["image_paths"] == [str(master)]
        assert req["model"] == "meta/muse-image/edit" and req["preferred_provider"] == "fal"
        assert req["warnings"] == []

    def test_build_is_deterministic(self, cast_dir, approve):
        cast = _load(cast_dir)
        approve(cast, "meera", "master")
        shot = {"description": "Meera at the window", "characters": [{"id": "meera", "expression": "shocked"}]}
        assert cb.build_shot(cast, shot) == cb.build_shot(cast, shot)

    def test_two_shot_orders_references_and_forbids_swaps(self, cast_dir, approve):
        cast = _load(cast_dir)
        meera_master = approve(cast, "meera", "master")
        raj_master = approve(cast, "raj", "master")
        req = cb.build_shot(
            cast,
            {
                "description": "An argument in the courtyard",
                "framing": "medium two-shot",
                "characters": [
                    {"id": "meera", "position": "left", "expression": "determined"},
                    {"id": "raj", "position": "right", "pose": "arms-crossed"},
                ],
            },
        )
        assert req["image_paths"] == [str(meera_master), str(raj_master)]
        assert [entry["character"] for entry in req["legend"]] == ["meera", "raj"]
        assert "Image 2 is the character reference for Raj." in req["prompt"]
        assert "Meera and Raj each keep their own face, hair and clothes; do not swap them." in req["prompt"]
        assert "on the left of the frame" in req["prompt"] and "on the right of the frame" in req["prompt"]
        assert "standing with arms crossed" in req["prompt"]  # pose text always included

    def test_pose_and_expression_images_follow_the_policy(self, cast_dir, approve):
        cast = _load(cast_dir)
        master = approve(cast, "meera", "master")
        pose = approve(cast, "meera", "pose", "doorway")
        expression = approve(cast, "meera", "expression", "shocked")
        spec = {"id": "meera", "pose": "doorway", "expression": "shocked"}

        close = cb.build_shot(cast, {"description": "x", "framing": "close-up", "characters": [spec]})
        assert close["image_paths"] == [str(master), str(pose), str(expression)]
        assert "Image 2 shows Meera's body pose; use it for the pose only." in close["prompt"]
        assert "Image 3 shows Meera's facial expression; use it for the expression only." in close["prompt"]

        wide = cb.build_shot(cast, {"description": "x", "framing": "wide shot", "characters": [spec]})
        assert wide["image_paths"] == [str(master), str(pose)]
        assert "eyes wide, eyebrows raised, lips parted" in wide["prompt"]  # expression text stays

    def test_outfit_reference_replaces_the_master_and_mismatched_pose_is_text_only(self, cast_dir, approve):
        cast = _load(cast_dir)
        approve(cast, "meera", "master")
        approve(cast, "meera", "pose", "doorway")  # drawn in the default outfit
        wedding = approve(cast, "meera", "outfit", "wedding")
        req = cb.build_shot(
            cast,
            {"description": "The wedding", "characters": [{"id": "meera", "outfit": "wedding", "pose": "doorway"}]},
        )
        assert req["image_paths"] == [str(wedding)]
        assert "red silk wedding saree" in req["prompt"]
        assert any("shows outfit 'home'" in w for w in req["warnings"])

    def test_missing_outfit_reference_warns_and_uses_the_master(self, cast_dir, approve):
        cast = _load(cast_dir)
        master = approve(cast, "meera", "master")
        req = cb.build_shot(cast, {"description": "x", "characters": [{"id": "meera", "outfit": "wedding"}]})
        assert req["image_paths"] == [str(master)]
        assert any("outfits/wedding.jpg" in w for w in req["warnings"])

    def test_cap_drops_lowest_priority_first_and_never_identity(self, cast_dir, approve, tmp_path):
        _write_settings(cast_dir, max_references=3)
        cast = _load(cast_dir)
        for character_id, pose, expression in (("meera", "doorway", "shocked"), ("raj", "arms-crossed", "angry")):
            approve(cast, character_id, "master")
            approve(cast, character_id, "pose", pose)
            approve(cast, character_id, "expression", expression)
        continuity = _png(tmp_path / "earlier.png")
        req = cb.build_shot(
            cast,
            {
                "description": "x",
                "framing": "close-up",
                "continuity_refs": [str(continuity)],
                "characters": [
                    {"id": "meera", "pose": "doorway", "expression": "shocked"},
                    {"id": "raj", "pose": "arms-crossed", "expression": "angry"},
                ],
            },
        )
        assert [(e["character"], e["kind"]) for e in req["legend"]] == [
            ("meera", "identity"), ("meera", "pose"), ("raj", "identity"),
        ]
        assert sum("dropped the" in w for w in req["warnings"]) == 4

        _write_settings(cast_dir, max_references=1)
        with pytest.raises(cb.CharacterBibleError, match="identity references"):
            cb.build_shot(_load(cast_dir), {"description": "x", "characters": [{"id": "meera"}, {"id": "raj"}]})

    @pytest.mark.parametrize(
        "spec, missing",
        [
            ({"id": "nobody"}, "nobody"),
            ({"id": "meera", "pose": "dancing"}, "dancing"),
            ({"id": "meera", "expression": "bored"}, "bored"),
            ({"id": "meera", "outfit": "pyjamas"}, "pyjamas"),
        ],
    )
    def test_unknown_ids_raise(self, cast_dir, spec, missing):
        with pytest.raises(cb.CharacterBibleError, match=missing):
            cb.build_shot(_load(cast_dir), {"description": "x", "characters": [spec]}, mode="text")

    def test_shorts_hint_and_vertical_aspect(self, cast_dir, approve):
        _write_settings(cast_dir, format_hints={"shorts": "faces in the upper third"})
        cast = _load(cast_dir)
        approve(cast, "meera", "master")
        req = cb.build_shot(
            cast, {"description": "x", "characters": [{"id": "meera"}]}, aspect_ratio="9:16", video_format="shorts"
        )
        assert "New scene, vertical 9:16: x." in req["prompt"]
        assert "Faces in the upper third." in req["prompt"]
        assert req["aspect_ratio"] == "9:16"

    def test_shot_without_characters_becomes_a_text_plate(self, cast_dir):
        req = cb.build_shot(_load(cast_dir), {"description": "An empty village lane at dusk"})
        assert req["mode"] == "text" and req["model"] == "flux/schnell"
        assert any("text-only plate" in w for w in req["warnings"])


class TestScenePlan:
    SCENE = {
        "id": "s07",
        "type": "character_scene",
        "description": "Meera finds the letter",
        "start_seconds": 30.0,
        "end_seconds": 35.0,
        "framing": "close-up",
        "character_actions": [
            {
                "character_id": "meera",
                "action_sequence": ["opens the drawer", "freezes"],
                "pose": "doorway",
                "expression": "shocked",
                "outfit": "home",
                "frame_position": "center",
            }
        ],
    }

    def test_scene_plan_schema_accepts_bible_fields(self):
        with open(REPO_ROOT / "schemas" / "artifacts" / "scene_plan.schema.json", encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate({"version": "1.0", "scenes": [self.SCENE]}, schema)

    def test_shot_from_scene_maps_character_actions(self):
        shot = cb.shot_from_scene(self.SCENE)
        assert shot["description"] == "Meera finds the letter" and shot["framing"] == "close-up"
        assert shot["characters"] == [
            {
                "id": "meera",
                "pose": "doorway",
                "expression": "shocked",
                "emotion": None,
                "outfit": "home",
                "position": "center",
                "action": "opens the drawer, then freezes",
            }
        ]

    def test_build_scene_uses_the_scene(self, cast_dir, approve):
        cast = _load(cast_dir)
        approve(cast, "meera", "master")
        req = cb.build_scene(cast, self.SCENE)
        assert "Meera: opens the drawer, then freezes;" in req["prompt"]


class TestReferenceJobs:
    def test_master_job_is_text_to_image(self, cast_dir):
        cast = _load(cast_dir)
        job = cb.build_ref_job(cast, "meera", "master")
        assert job["mode"] == "text" and job["model"] == "flux/schnell"
        assert job["num_candidates"] == 4
        assert cb.identity_text(cast.character("meera")) in job["prompt"]
        assert "plain light-grey studio background" in job["prompt"]
        assert job["target"].replace("\\", "/").endswith("meera/refs/master.jpg")

    def test_other_jobs_need_the_master(self, cast_dir):
        with pytest.raises(cb.CharacterBibleError, match="approve the master"):
            cb.build_ref_job(_load(cast_dir), "meera", "pose", "doorway")

    def test_pose_job_draws_from_the_master(self, cast_dir, approve):
        cast = _load(cast_dir)
        master = approve(cast, "meera", "master")
        job = cb.build_ref_job(cast, "meera", "pose", "doorway")
        assert job["image_paths"] == [str(master)]
        assert cb.lock_clause(cast.character("meera")) in job["prompt"]
        assert "new pose: standing in a doorway, one hand on the door frame." in job["prompt"]
        assert job["aspect_ratio"] == "2:3" and job["preferred_provider"] == "fal"

    def test_pose_in_another_outfit_draws_from_that_outfit(self, cast_dir, approve):
        cast = _load(cast_dir)
        approve(cast, "meera", "master")
        with pytest.raises(cb.CharacterBibleError, match="'wedding' outfit reference"):
            cb.build_ref_job(cast, "meera", "pose", "doorway", outfit="wedding")
        wedding = approve(cast, "meera", "outfit", "wedding")
        job = cb.build_ref_job(cast, "meera", "pose", "doorway", outfit="wedding")
        assert job["image_paths"] == [str(wedding)] and job["outfit"] == "wedding"

    def test_outfit_job_changes_only_the_clothes(self, cast_dir, approve):
        cast = _load(cast_dir)
        approve(cast, "meera", "master")
        job = cb.build_ref_job(cast, "meera", "outfit", "wedding")
        meera = cast.character("meera")
        assert cb.lock_clause(meera, include_outfit=False) in job["prompt"]
        assert f"Change only the clothes to: {meera.outfit('wedding')['description']}." in job["prompt"]

    def test_variant_keeps_everything_but_one_change(self, tmp_path):
        still = _png(tmp_path / "still.png")
        req = cb.build_variant(still, "her eyes closed mid-blink.")
        assert req["prompt"].startswith("Keep image 1 exactly the same")
        assert "Change only this: her eyes closed mid-blink." in req["prompt"]
        assert req["image_paths"] == [str(still)]


class TestApproval:
    def test_approve_writes_a_small_jpeg_and_a_sidecar(self, cast_dir, tmp_path):
        cast = _load(cast_dir)
        big = _png(tmp_path / "big.png", size=(3000, 2000))
        target = cb.approve_ref(
            cast, "meera", "master", big,
            provenance={"model": "flux/schnell", "cost_usd": 0.003, "identity_hash": "forged"},
        )
        with Image.open(target) as image:
            assert image.format == "JPEG" and max(image.size) <= cb.REF_MAX_SIDE
        sidecar = json.loads(target.with_suffix(".json").read_text(encoding="utf-8"))
        meera = cast.character("meera")
        assert sidecar["model"] == "flux/schnell" and sidecar["outfit"] == "home"
        assert sidecar["identity_hash"] == meera.identity_hash()  # provenance can't forge it
        assert meera.ref_state("master") == "approved"

    def test_master_first_and_known_items_only(self, cast_dir, approve):
        cast = _load(cast_dir)
        with pytest.raises(cb.CharacterBibleError, match="master reference first"):
            approve(cast, "meera", "pose", "doorway")
        approve(cast, "meera", "master")
        with pytest.raises(cb.CharacterBibleError, match="dancing"):
            approve(cast, "meera", "pose", "dancing")

    def test_replace_supersedes_instead_of_deleting(self, cast_dir, approve):
        cast = _load(cast_dir)
        approve(cast, "meera", "master")
        with pytest.raises(cb.CharacterBibleError, match="already approved"):
            approve(cast, "meera", "master")
        approve(cast, "meera", "master", replace=True)
        archived = sorted(p.suffix for p in (cast_dir / "meera" / "refs" / "_superseded").iterdir())
        assert archived == [".jpg", ".json"]

    def test_identity_edit_makes_references_stale_until_rehash(self, cast_dir, approve):
        cast = _load(cast_dir)
        approve(cast, "meera", "master")
        edited = _example(id="meera")
        edited["identity"]["hair"] = "long black hair in a single braid"
        _write_character(cast_dir, edited)
        cast = _load(cast_dir)
        assert cast.character("meera").ref_state("master") == "stale"
        shot = {"description": "x", "characters": [{"id": "meera"}]}
        with pytest.raises(cb.CharacterBibleError, match="older description"):
            cb.build_shot(cast, shot)
        assert any("older description" in w for w in cb.build_shot(cast, shot, allow_stale=True)["warnings"])

        assert len(cb.rehash(cast, "meera")) == 1
        assert cast.character("meera").ref_state("master") == "approved"

    def test_stale_pose_text_drops_only_the_pose_image(self, cast_dir, approve):
        cast = _load(cast_dir)
        master = approve(cast, "meera", "master")
        approve(cast, "meera", "pose", "doorway")
        edited = _example(id="meera")
        edited["poses"]["doorway"] = "leaning on the door frame, arms folded"
        _write_character(cast_dir, edited)
        cast = _load(cast_dir)
        req = cb.build_shot(cast, {"description": "x", "characters": [{"id": "meera", "pose": "doorway"}]})
        assert req["image_paths"] == [str(master)]
        assert any("pose image 'doorway' is stale" in w for w in req["warnings"])

    def test_status_reports_what_is_left(self, cast_dir, approve):
        cast = _load(cast_dir)
        approve(cast, "meera", "master")
        report = cb.cast_status(cast)["meera"]
        assert report["master"] == "approved" and report["poses"]["doorway"] == "missing"
        assert any("set status: locked" in w for w in report["warnings"])


class TestToolsAround:
    def test_contact_sheet_tiles_images(self, tmp_path):
        images = [_png(tmp_path / f"c{i}.png", size=(100, 150)) for i in range(3)]
        sheet = cb.contact_sheet(images, tmp_path / "sheet.jpg", columns=2, thumb=200)
        with Image.open(sheet) as image:
            assert image.size == (400, 2 * (200 + 28))

    def test_cli_dry_run_and_errors(self, cast_dir, tmp_path, capsys):
        spec = tmp_path / "shot.json"
        spec.write_text(json.dumps({"description": "Meera at the well", "characters": [{"id": "meera"}]}), encoding="utf-8")
        assert cb.main(["shot", "--cast-dir", str(cast_dir), "--spec", str(spec), "--mode", "text"]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["mode"] == "text" and "Meera at the well" in out["prompt"]

        assert cb.main(["show", "--cast-dir", str(cast_dir), "nobody"]) == 1
        assert "nobody" in capsys.readouterr().err
