"""Channel profile loader.

A channel profile (channels/<id>/channel.yaml) holds the standing creative
defaults for one YouTube channel: language, format, pipeline, style playbook,
narration voice, script rules and visual approach. Agents load it at the start
of a production to pre-fill proposal decisions — see
skills/meta/channel-profiles.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import yaml
import jsonschema

from lib.media_profiles import ALL_PROFILES as MEDIA_PROFILES
from lib.pipeline_loader import PIPELINE_DEFS_DIR
from styles.playbook_loader import load_playbook

CHANNELS_DIR = Path(__file__).resolve().parent.parent / "channels"
SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "schemas"
    / "channels"
    / "channel_profile.schema.json"
)
PROFILE_FILENAME = "channel.yaml"


class ChannelProfileError(ValueError):
    """A channel profile is missing, malformed, or references something that doesn't exist."""


def _load_profile_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def channel_dir(channel_id: str, channels_dir: Optional[Path] = None) -> Path:
    """Return the folder holding a channel's profile and guides."""
    return (channels_dir or CHANNELS_DIR) / channel_id


def list_channels(channels_dir: Optional[Path] = None) -> list[str]:
    """List channel ids. Folders starting with '_' (e.g. _template) are skipped."""
    channels_dir = channels_dir or CHANNELS_DIR
    if not channels_dir.is_dir():
        return []
    return sorted(
        p.name
        for p in channels_dir.iterdir()
        if p.is_dir() and not p.name.startswith("_") and (p / PROFILE_FILENAME).exists()
    )


def validate_channel(profile: dict, folder: Path) -> None:
    """Validate a profile against the schema and check every reference resolves.

    Raises ChannelProfileError naming the first problem found.
    """
    try:
        jsonschema.validate(instance=profile, schema=_load_profile_schema())
    except jsonschema.ValidationError as exc:
        path = "/".join(str(p) for p in exc.absolute_path) or "<root>"
        raise ChannelProfileError(f"{folder.name}: {path}: {exc.message}") from exc

    if not folder.name.startswith("_") and profile["id"] != folder.name:
        raise ChannelProfileError(
            f"{folder.name}: id '{profile['id']}' must match the folder name"
        )

    production = profile["production"]
    formats = profile["formats"]
    pipelines = [
        production["default_pipeline"],
        *production.get("alternate_pipelines", {}).values(),
        *(fmt["pipeline"] for fmt in formats.values() if "pipeline" in fmt),
    ]
    for name in pipelines:
        if not (PIPELINE_DEFS_DIR / f"{name}.yaml").exists():
            raise ChannelProfileError(f"{folder.name}: pipeline '{name}' not found in pipeline_defs/")

    try:
        load_playbook(production["style_playbook"])
    except FileNotFoundError as exc:
        raise ChannelProfileError(f"{folder.name}: {exc}") from exc
    except jsonschema.ValidationError as exc:
        raise ChannelProfileError(
            f"{folder.name}: playbook '{production['style_playbook']}' is invalid: {exc.message}"
        ) from exc

    for format_name, fmt in formats.items():
        if fmt["media_profile"] not in MEDIA_PROFILES:
            raise ChannelProfileError(
                f"{folder.name}: formats.{format_name}.media_profile "
                f"'{fmt['media_profile']}' not in lib/media_profiles.py"
            )

    for label, rel in (
        ("script.guide", profile["script"]["guide"]),
        ("visuals.character_bible", profile["visuals"].get("character_bible")),
        ("visuals.cast_dir", profile["visuals"].get("cast_dir")),
    ):
        if rel and not (folder / rel).exists():
            raise ChannelProfileError(f"{folder.name}: {label} path '{rel}' not found")


def load_channel(channel_id: str, channels_dir: Optional[Path] = None) -> dict[str, Any]:
    """Load and validate a channel profile by id.

    Args:
        channel_id: Folder name under channels/.
        channels_dir: Override directory for channel folders.

    Returns:
        Validated profile dict.
    """
    folder = channel_dir(channel_id, channels_dir)
    path = folder / PROFILE_FILENAME
    if not path.exists():
        available = ", ".join(list_channels(channels_dir)) or "none"
        raise ChannelProfileError(f"Channel not found: {path} (available: {available})")

    with open(path, encoding="utf-8") as f:
        profile = yaml.safe_load(f)

    validate_channel(profile, folder)
    return profile


def resolve_format(profile: dict[str, Any], video_format: str) -> dict[str, Any]:
    """Return one format's settings with channel-level defaults filled in.

    The result always has ``pipeline`` (the format's override, else
    production.default_pipeline) plus everything in formats.<video_format>.
    """
    formats = profile["formats"]
    if video_format not in formats:
        raise ChannelProfileError(
            f"{profile['id']}: no '{video_format}' format (has: {', '.join(formats)})"
        )
    return {"pipeline": profile["production"]["default_pipeline"], **formats[video_format]}
