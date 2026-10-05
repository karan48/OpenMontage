"""Character bible: canonical character records -> approved reference images -> scene prompts.

A cast lives in a channel folder (channels/<id>/<visuals.cast_dir>/) and, for
story-only characters, in a project (projects/<id>/cast/). Each character is a
folder holding a human-edited character.yaml (the locked description) and
refs/ (approved images, each with a JSON provenance sidecar).

This module loads and checks casts, assembles image prompts and ordered
reference lists from them, and saves approved references. It never rewrites
character.yaml, and it makes no creative choices: what a scene shows, which
pose and which expression stay with the agent. See
skills/meta/character-bible.md.

CLI: python -m lib.character_bible --help
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import jsonschema
import yaml

from lib.paths import PROJECTS_DIR, REPO_ROOT

SCHEMA_DIR = REPO_ROOT / "schemas" / "channels"
CHARACTER_FILENAME = "character.yaml"
CAST_SETTINGS_FILENAME = "cast.yaml"
REFS_DIRNAME = "refs"
SUPERSEDED_DIRNAME = "_superseded"
REF_MAX_SIDE = 1536
REF_JPEG_QUALITY = 92

REF_KINDS = ("master", "turnaround", "outfit", "pose", "expression")

DEFAULT_SETTINGS: dict[str, Any] = {
    "style": {"source": "playbook", "line": None},
    "no_text_clause": "No text, no letters, no numbers, no signs, no logos, no watermark.",
    "sheet_background": "plain light-grey studio background, even soft lighting",
    "models": {
        "reference": "meta/muse-image/edit",
        "reference_fallback": "fal-ai/flux-pro/kontext",
        "master": "flux/schnell",
        "plates": "flux/schnell",
    },
    "max_references": 10,
    "master_candidates": 4,
    "reference_policy": {
        "identity": "master",
        "pose_image": "when_outfit_matches",
        "expression_image": "closeups",
    },
    "format_hints": {},
    "ref_aspect": {
        "master": "2:3",
        "turnaround": "16:9",
        "outfit": "2:3",
        "pose": "2:3",
        "expression": "1:1",
    },
}

_ASPECT_PHRASES = {
    "16:9": "wide 16:9",
    "9:16": "vertical 9:16",
    "1:1": "square 1:1",
    "4:5": "vertical 4:5",
    "2:3": "vertical 2:3",
    "3:2": "wide 3:2",
    "21:9": "ultra-wide 21:9",
}

# flux_image takes width/height, not an aspect ratio (about 1 MP, multiples of 64).
_FLUX_SIZES = {
    "16:9": (1344, 768),
    "9:16": (768, 1344),
    "1:1": (1024, 1024),
    "4:5": (896, 1120),
    "2:3": (832, 1248),
    "3:2": (1248, 832),
    "21:9": (1536, 640),
}

_POSITIONS = {
    "left": "on the left of the frame",
    "center": "in the centre of the frame",
    "right": "on the right of the frame",
    "background": "in the background",
    "foreground": "in the foreground",
}

# Reference priority when a shot exceeds the model's reference cap: the
# highest number is dropped first. Identity is never dropped.
_PRIORITY = {"identity": 0, "pose": 1, "expression": 2, "turnaround": 3, "continuity": 4}


class CharacterBibleError(ValueError):
    """A cast or character is missing, malformed, or asked for something it doesn't have."""


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


def _sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class Character:
    """One character folder: the validated character.yaml plus its refs/."""

    data: dict[str, Any]
    root: Path
    scope: str  # "channel" or "story"

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def identity(self) -> dict[str, str]:
        return self.data["identity"]

    @property
    def default_outfit(self) -> str:
        return self.data["wardrobe"]["default"]

    def outfit_id(self, outfit: Optional[str]) -> str:
        """Resolve an outfit id (None means the default) and check it exists."""
        outfit = outfit or self.default_outfit
        if outfit not in self.data["wardrobe"]["outfits"]:
            known = ", ".join(self.data["wardrobe"]["outfits"])
            raise CharacterBibleError(f"{self.name}: no outfit '{outfit}' (has: {known})")
        return outfit

    def outfit(self, outfit: Optional[str] = None) -> dict[str, str]:
        return self.data["wardrobe"]["outfits"][self.outfit_id(outfit)]

    def _item_text(self, table: str, item: str) -> str:
        entries = self.data.get(table) or {}
        if item not in entries:
            known = ", ".join(entries) or "none"
            raise CharacterBibleError(f"{self.name}: no {table[:-1]} '{item}' (has: {known})")
        return entries[item]

    def pose_text(self, pose: str) -> str:
        return self._item_text("poses", pose)

    def expression_text(self, expression: str) -> str:
        return self._item_text("expressions", expression)

    # --- approved reference files -------------------------------------------

    def ref_path(self, kind: str, item: Optional[str] = None) -> Path:
        refs = self.root / REFS_DIRNAME
        if kind in ("master", "turnaround"):
            return refs / f"{kind}.jpg"
        if kind in ("outfit", "pose", "expression"):
            if not item:
                raise CharacterBibleError(f"{self.name}: a {kind} reference needs an item id")
            return refs / f"{kind}s" / f"{item}.jpg"
        raise CharacterBibleError(f"unknown reference kind '{kind}' (use one of {', '.join(REF_KINDS)})")

    def sidecar_path(self, kind: str, item: Optional[str] = None) -> Path:
        return self.ref_path(kind, item).with_suffix(".json")

    def has_ref(self, kind: str, item: Optional[str] = None) -> bool:
        return self.ref_path(kind, item).exists()

    def read_sidecar(self, kind: str, item: Optional[str] = None) -> Optional[dict[str, Any]]:
        path = self.sidecar_path(kind, item)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # --- staleness ----------------------------------------------------------

    def identity_hash(self) -> str:
        return _sha(self.identity)

    def item_hash(self, kind: str, item: Optional[str], outfit: str) -> str:
        """Hash of the text a reference was drawn from, besides the identity."""
        text = None
        if kind == "pose":
            text = self.pose_text(item)
        elif kind == "expression":
            text = self.expression_text(item)
        return _sha({"kind": kind, "text": text, "outfit": self.outfit(outfit)["description"]})

    def ref_state(self, kind: str, item: Optional[str] = None) -> str:
        """approved | missing | stale | unverified (image without a sidecar)."""
        if not self.has_ref(kind, item):
            return "missing"
        side = self.read_sidecar(kind, item)
        if side is None:
            return "unverified"
        if side.get("identity_hash") != self.identity_hash():
            return "stale"
        outfit = side.get("outfit") or self.default_outfit
        if outfit not in self.data["wardrobe"]["outfits"]:
            return "stale"
        try:
            current = self.item_hash(kind, item, outfit)
        except CharacterBibleError:
            return "stale"
        return "approved" if side.get("item_hash") == current else "stale"


@dataclass
class Cast:
    """All characters available to a production, plus cast-wide settings."""

    settings: dict[str, Any]
    style_line: str
    style_prefix: str
    negative_prompt: str
    characters: dict[str, Character] = field(default_factory=dict)
    channel_id: Optional[str] = None

    def character(self, character_id: str) -> Character:
        if character_id not in self.characters:
            known = ", ".join(self.characters) or "none"
            raise CharacterBibleError(f"no character '{character_id}' in the cast (has: {known})")
        return self.characters[character_id]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load_schema(name: str) -> dict:
    with open(SCHEMA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _validate(instance: Any, schema_name: str, label: str) -> None:
    try:
        jsonschema.validate(instance=instance, schema=_load_schema(schema_name))
    except jsonschema.ValidationError as exc:
        path = "/".join(str(p) for p in exc.absolute_path) or "<root>"
        raise CharacterBibleError(f"{label}: {path}: {exc.message}") from exc


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _read_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_character(folder: Path, scope: str = "channel") -> Character:
    """Load and validate one character folder."""
    path = folder / CHARACTER_FILENAME
    if not path.exists():
        raise CharacterBibleError(f"{folder}: no {CHARACTER_FILENAME}")
    data = _read_yaml(path)
    _validate(data, "character.schema.json", str(path))
    if data["id"] != folder.name.lstrip("_"):
        raise CharacterBibleError(f"{path}: id '{data['id']}' must match the folder name '{folder.name}'")
    if data["wardrobe"]["default"] not in data["wardrobe"]["outfits"]:
        raise CharacterBibleError(
            f"{path}: wardrobe.default '{data['wardrobe']['default']}' is not one of wardrobe.outfits"
        )
    return Character(data=data, root=folder, scope=scope)


def load_cast_from_dir(
    cast_dir: Path,
    *,
    playbook: Optional[dict] = None,
    story_dirs: tuple[Path, ...] | list[Path] = (),
    include_underscored: bool = False,
    channel_id: Optional[str] = None,
) -> Cast:
    """Load a cast folder (plus optional story cast folders) into a Cast.

    Folders whose names start with '_' (examples, _superseded) are skipped
    unless include_underscored is set. A character id may appear only once
    across all folders.
    """
    cast_dir = Path(cast_dir)
    if not cast_dir.is_dir():
        raise CharacterBibleError(f"cast folder not found: {cast_dir}")

    settings = copy.deepcopy(DEFAULT_SETTINGS)
    settings_path = cast_dir / CAST_SETTINGS_FILENAME
    if settings_path.exists():
        raw = _read_yaml(settings_path) or {}
        _validate(raw, "cast.schema.json", str(settings_path))
        settings = _merge(settings, raw)

    generation = (playbook or {}).get("asset_generation", {})
    if settings["style"]["source"] == "inline":
        line = (settings["style"].get("line") or "").strip()
        if not line:
            raise CharacterBibleError(f"{settings_path}: style.source is inline but style.line is empty")
        prefix = line.rstrip(" ,.") + ", "
    else:
        prefix = generation.get("image_prompt_prefix") or ""
        if not prefix.strip():
            raise CharacterBibleError(
                f"{cast_dir}: style.source is playbook, but no playbook with an image_prompt_prefix was given"
            )
    style_line = prefix.strip().rstrip(",. ")

    cast = Cast(
        settings=settings,
        style_line=style_line,
        style_prefix=prefix if prefix.endswith(" ") else prefix + " ",
        negative_prompt=generation.get("image_negative_prompt", ""),
        channel_id=channel_id,
    )

    seen: dict[str, Path] = {}
    for scope, folder in [("channel", cast_dir), *(("story", Path(d)) for d in story_dirs)]:
        if not folder.is_dir():
            continue
        for sub in sorted(folder.iterdir()):
            if not sub.is_dir():
                continue
            if sub.name.startswith("_") and not include_underscored:
                continue
            if sub.name == SUPERSEDED_DIRNAME:
                continue
            character = load_character(sub, scope)
            if character.id in seen:
                raise CharacterBibleError(
                    f"character '{character.id}' is defined twice: {seen[character.id]} and {sub}"
                )
            seen[character.id] = sub
            cast.characters[character.id] = character
    return cast


def load_cast(
    channel_id: str,
    project_id: Optional[str] = None,
    *,
    channels_dir: Optional[Path] = None,
    projects_dir: Optional[Path] = None,
    include_underscored: bool = False,
) -> Cast:
    """Load a channel's cast, plus a project's story cast when project_id is given."""
    from lib.channel_profile import channel_dir, load_channel
    from styles.playbook_loader import load_playbook

    profile = load_channel(channel_id, channels_dir)
    cast_rel = profile["visuals"].get("cast_dir")
    if not cast_rel:
        raise CharacterBibleError(
            f"{channel_id}: visuals.cast_dir is not set, so this channel has no structured character bible"
        )
    story_dirs = []
    if project_id:
        story_dirs.append((projects_dir or PROJECTS_DIR) / project_id / "cast")
    return load_cast_from_dir(
        channel_dir(channel_id, channels_dir) / cast_rel,
        playbook=load_playbook(profile["production"]["style_playbook"]),
        story_dirs=story_dirs,
        include_underscored=include_underscored,
        channel_id=channel_id,
    )


# ---------------------------------------------------------------------------
# Canonical text
# ---------------------------------------------------------------------------


def _join_and(items: list[str]) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def identity_text(character: Character, outfit: Optional[str] = None) -> str:
    """The full locked look, verbatim, for text-only prompts."""
    ident = character.identity
    parts = [f"{character.name}, {ident['summary']}"]
    parts += [ident[k] for k in ("face", "eyes", "hair", "skin", "build", "marks", "accessories") if ident.get(k)]
    parts.append("wearing " + character.outfit(outfit)["description"])
    return ", ".join(parts)


def lock_clause(character: Character, outfit: Optional[str] = None, *, include_outfit: bool = True) -> str:
    """The 'keep exact …' sentence that pins a reference image's identity."""
    ident = character.identity
    items = ["face", "eyes", "eyebrows", "skin tone", "body proportions", ident["hair"]]
    items += [ident[k] for k in ("marks", "accessories") if ident.get(k)]
    if include_outfit:
        chosen = character.outfit(outfit)
        items.append(chosen.get("short") or chosen["description"])
    return f"Keep {character.name}'s exact {_join_and(items)}."


def _aspect_phrase(aspect_ratio: Optional[str]) -> str:
    if not aspect_ratio:
        return ""
    return _ASPECT_PHRASES.get(aspect_ratio, aspect_ratio)


def _flux_size(aspect_ratio: Optional[str]) -> tuple[int, int]:
    if aspect_ratio in _FLUX_SIZES:
        return _FLUX_SIZES[aspect_ratio]
    try:
        w, h = (int(x) for x in str(aspect_ratio).split(":"))
    except ValueError:
        return (1024, 1024)
    scale = (1024 * 1024 / (w * h)) ** 0.5
    return (max(64, round(w * scale / 64) * 64), max(64, round(h * scale / 64) * 64))


def _is_closeup(framing: str) -> bool:
    return "close" in (framing or "").lower()


def _sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    return text if text.endswith((".", "!", "?")) else text + "."


# ---------------------------------------------------------------------------
# Shots
# ---------------------------------------------------------------------------


@dataclass
class _Ref:
    path: Path
    kind: str
    sentence: str
    character: Optional[str] = None

    @property
    def priority(self) -> int:
        return _PRIORITY[self.kind]


def shot_from_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """Turn a scene_plan scene into a shot spec for build_shot()."""
    characters = []
    for action in scene.get("character_actions") or []:
        characters.append(
            {
                "id": action["character_id"],
                "pose": action.get("pose"),
                "expression": action.get("expression"),
                "emotion": action.get("emotion"),
                "outfit": action.get("outfit"),
                "position": action.get("frame_position"),
                "action": ", then ".join(action.get("action_sequence") or []),
            }
        )
    return {
        "id": scene.get("id"),
        "description": scene["description"],
        "framing": scene.get("framing") or "",
        "characters": characters,
    }


def _check_identity(character: Character, kind: str, item: Optional[str], allow_stale: bool, warnings: list) -> None:
    state = character.ref_state(kind, item)
    label = character.ref_path(kind, item).relative_to(character.root).as_posix()
    if state == "stale":
        message = (
            f"{character.name}: {label} was approved for an older description. Revert the text, "
            f"re-approve the image, or run `rehash` if the edit was cosmetic"
        )
        if not allow_stale:
            raise CharacterBibleError(message)
        warnings.append(message)
    elif state == "unverified":
        warnings.append(f"{character.name}: {label} has no provenance sidecar (not approved through approve_ref)")


def _identity_refs(cast: Cast, character: Character, outfit: str, allow_stale: bool, warnings: list) -> list[_Ref]:
    sentence = f"Image {{n}} is the character reference for {character.name}."
    if not character.has_ref("master"):
        raise CharacterBibleError(
            f"{character.name} has no approved master reference ({REFS_DIRNAME}/master.jpg). "
            "Run the cast sub-stage first (skills/meta/character-bible.md)."
        )
    primary_kind, primary_item = "master", None
    if outfit != character.default_outfit:
        if character.has_ref("outfit", outfit):
            primary_kind, primary_item = "outfit", outfit
        else:
            warnings.append(
                f"{character.name}: no approved {REFS_DIRNAME}/outfits/{outfit}.jpg, so the reference shows the "
                f"default outfit while the prompt asks for '{outfit}'. Approve an outfit reference first."
            )
    _check_identity(character, primary_kind, primary_item, allow_stale, warnings)
    refs = [_Ref(character.ref_path(primary_kind, primary_item), "identity", sentence, character.id)]

    policy = cast.settings["reference_policy"]["identity"]
    if policy in ("turnaround", "master_and_turnaround") and primary_kind == "master":
        if character.ref_state("turnaround") in ("approved", "unverified"):
            turnaround = _Ref(
                character.ref_path("turnaround"),
                "turnaround",
                f"Image {{n}} is {character.name}'s turnaround sheet (front, three-quarter, side and back views).",
                character.id,
            )
            if policy == "turnaround":
                turnaround.kind = "identity"
                turnaround.sentence = sentence
                refs = [turnaround]
            else:
                refs.append(turnaround)
        else:
            warnings.append(f"{character.name}: identity policy wants the turnaround, which isn't approved yet")
    return refs


def _optional_ref(character: Character, kind: str, item: str, sentence: str, warnings: list) -> Optional[_Ref]:
    state = character.ref_state(kind, item)
    if state == "missing":
        return None
    if state == "stale":
        warnings.append(f"{character.name}: {kind} image '{item}' is stale, so the shot uses its text only")
        return None
    return _Ref(character.ref_path(kind, item), kind, sentence, character.id)


def _cap(refs: list[_Ref], limit: int, warnings: list) -> list[_Ref]:
    if len(refs) <= limit:
        return refs
    removable = sorted(
        (i for i, r in enumerate(refs) if r.kind != "identity"),
        key=lambda i: (refs[i].priority, i),
        reverse=True,
    )
    drop: set[int] = set()
    for index in removable:
        if len(refs) - len(drop) <= limit:
            break
        drop.add(index)
    if len(refs) - len(drop) > limit:
        raise CharacterBibleError(
            f"this shot needs {len(refs) - len(drop)} identity references but the model takes {limit}; "
            "split the shot or show fewer characters"
        )
    for index in sorted(drop):
        ref = refs[index]
        warnings.append(f"dropped the {ref.kind} reference for {ref.character or 'the scene'} to stay within {limit} images")
    return [r for i, r in enumerate(refs) if i not in drop]


def _character_line(character: Character, spec: dict, pose_text: Optional[str], expression_text: Optional[str]) -> str:
    bits = []
    if spec.get("action"):
        bits.append(spec["action"].strip().rstrip("."))
    if pose_text:
        bits.append(pose_text.strip().rstrip("."))
    if expression_text:
        bits.append(expression_text.strip().rstrip("."))
    if spec.get("position"):
        bits.append(_POSITIONS.get(spec["position"], spec["position"]))
    if not bits:
        return ""
    return f"{character.name}: " + "; ".join(bits) + "."


def build_shot(
    cast: Cast,
    shot: dict[str, Any],
    *,
    aspect_ratio: str = "16:9",
    video_format: Optional[str] = None,
    mode: str = "reference",
    allow_stale: bool = False,
) -> dict[str, Any]:
    """Assemble one shot's image request from the bible.

    shot = {"description": str, "framing": str, "continuity_refs": [path, ...],
            "characters": [{"id", "pose", "expression", "emotion", "outfit", "position", "action"}]}

    mode="reference" returns a request for a reference-conditioned model
    (fal_reference_image); mode="text" returns a text-only request
    (flux_image). A shot with no bible character and no continuity frame is
    always built as a text-only plate. The result can be passed straight to
    image_selector after adding output_path.
    """
    if mode not in ("reference", "text"):
        raise CharacterBibleError(f"unknown mode '{mode}' (use reference or text)")
    description = (shot.get("description") or "").strip()
    if not description:
        raise CharacterBibleError("a shot needs a description")
    framing = (shot.get("framing") or "").strip()
    continuity = [Path(p) for p in shot.get("continuity_refs") or []]
    warnings: list[str] = []

    resolved = []
    for spec in shot.get("characters") or []:
        if not spec.get("id"):
            raise CharacterBibleError("each character in a shot needs an id")
        character = cast.character(spec["id"])
        outfit = character.outfit_id(spec.get("outfit"))
        pose_text = character.pose_text(spec["pose"]) if spec.get("pose") else None
        if spec.get("expression"):
            expression_text = character.expression_text(spec["expression"])
        else:
            expression_text = spec.get("emotion")
        resolved.append((character, spec, outfit, pose_text, expression_text))

    if mode == "reference" and not resolved and not continuity:
        mode = "text"
        warnings.append("no bible character in this shot, so it is built as a text-only plate")

    scene_line = f"{_aspect_phrase(aspect_ratio)} {framing}".strip()
    scene_text = f"{scene_line}: {description.rstrip('.')}." if scene_line else f"{description.rstrip('.')}."
    format_hint = cast.settings["format_hints"].get(video_format or "", "")
    character_lines = [_character_line(c, s, p, e) for c, s, _, p, e in resolved]
    names = [c.name for c, *_ in resolved]
    two_shot = []
    if len(resolved) >= 2:
        two_shot.append(f"{_join_and(names)} each keep their own face, hair and clothes; do not swap them.")

    if mode == "text":
        model = cast.settings["models"]["plates"]
        width, height = _flux_size(aspect_ratio)
        parts = [cast.style_prefix + scene_text]
        for character, _spec, outfit, _pose, _expression in resolved:
            parts.append(_sentence(identity_text(character, outfit)))
        parts += [line for line in character_lines if line]
        parts += two_shot
        parts += [_sentence(format_hint), cast.settings["no_text_clause"]]
        return {
            "mode": "text",
            "prompt": " ".join(p for p in parts if p),
            "negative_prompt": cast.negative_prompt,
            "image_paths": [],
            "legend": [],
            "aspect_ratio": aspect_ratio,
            "width": width,
            "height": height,
            "model": model,
            "preferred_provider": "flux",
            "characters": [c.id for c, *_ in resolved],
            "warnings": warnings,
        }

    policy = cast.settings["reference_policy"]
    refs: list[_Ref] = []
    for character, spec, outfit, pose_text, expression_text in resolved:
        refs += _identity_refs(cast, character, outfit, allow_stale, warnings)
        pose = spec.get("pose")
        if pose and policy["pose_image"] != "never":
            ref = _optional_ref(
                character, "pose", pose,
                f"Image {{n}} shows {character.name}'s body pose; use it for the pose only.", warnings,
            )
            if ref is not None:
                side = character.read_sidecar("pose", pose) or {}
                ref_outfit = side.get("outfit") or character.default_outfit
                if policy["pose_image"] == "attach" or ref_outfit == outfit:
                    refs.append(ref)
                else:
                    warnings.append(
                        f"{character.name}: pose image '{pose}' shows outfit '{ref_outfit}' but the shot uses "
                        f"'{outfit}', so the shot uses the pose text only"
                    )
        expression = spec.get("expression")
        if expression and policy["expression_image"] != "never":
            if policy["expression_image"] == "always" or _is_closeup(framing):
                ref = _optional_ref(
                    character, "expression", expression,
                    f"Image {{n}} shows {character.name}'s facial expression; use it for the expression only.",
                    warnings,
                )
                if ref is not None:
                    refs.append(ref)
    for path in continuity:
        refs.append(
            _Ref(path, "continuity", "Image {n} is an earlier frame of this scene; match its setting, lighting and camera.")
        )
    refs = _cap(refs, int(cast.settings["max_references"]), warnings)

    parts = [r.sentence.format(n=n) for n, r in enumerate(refs, 1)]
    for character, _spec, outfit, _pose, _expression in resolved:
        parts.append(lock_clause(character, outfit))
        if character.data.get("ref_notes"):
            parts.append(_sentence(character.data["ref_notes"]))
    if resolved:
        parts.append("Ignore the plain backgrounds of the character reference images.")
    parts.append(f"New scene, {scene_text}" if scene_line else f"New scene: {scene_text}")
    parts += [line for line in character_lines if line]
    parts += two_shot
    parts += [_sentence(format_hint), _sentence(cast.style_line), cast.settings["no_text_clause"]]

    return {
        "mode": "reference",
        "prompt": " ".join(p for p in parts if p),
        "image_paths": [str(r.path) for r in refs],
        "legend": [
            {"index": n, "kind": r.kind, "character": r.character, "path": str(r.path)}
            for n, r in enumerate(refs, 1)
        ],
        "aspect_ratio": aspect_ratio,
        "model": cast.settings["models"]["reference"],
        "preferred_provider": "fal",
        "characters": [c.id for c, *_ in resolved],
        "warnings": warnings,
    }


def build_scene(cast: Cast, scene: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """build_shot() for a scene_plan scene."""
    return build_shot(cast, shot_from_scene(scene), **kwargs)


# ---------------------------------------------------------------------------
# Building the bible itself
# ---------------------------------------------------------------------------


def build_ref_job(
    cast: Cast,
    character_id: str,
    kind: str,
    item: Optional[str] = None,
    *,
    outfit: Optional[str] = None,
) -> dict[str, Any]:
    """Assemble the request that draws one bible reference image.

    master is text-to-image (several candidates, the user picks one). Every
    other kind is drawn from the approved master (or the approved outfit
    reference), so each image the model ever sees shows the same person.
    """
    character = cast.character(character_id)
    s = cast.settings
    background = s["sheet_background"]
    no_text = s["no_text_clause"]
    aspect = s["ref_aspect"][kind] if kind in s["ref_aspect"] else "1:1"
    warnings: list[str] = []

    if kind == "master":
        if item:
            raise CharacterBibleError("a master reference takes no item")
        width, height = _flux_size(aspect)
        prompt = (
            f"{cast.style_prefix}character model sheet: {identity_text(character)}, full body, standing straight "
            f"and facing the camera, arms relaxed at the sides, calm neutral expression, {background}. {no_text}"
        )
        return {
            "mode": "text",
            "kind": "master",
            "item": None,
            "outfit": character.default_outfit,
            "prompt": prompt,
            "negative_prompt": cast.negative_prompt,
            "image_paths": [],
            "legend": [],
            "aspect_ratio": aspect,
            "width": width,
            "height": height,
            "model": s["models"]["master"],
            "preferred_provider": "flux",
            "num_candidates": s["master_candidates"],
            "target": str(character.ref_path("master")),
            "warnings": warnings,
        }

    if kind not in REF_KINDS:
        raise CharacterBibleError(f"unknown reference kind '{kind}' (use one of {', '.join(REF_KINDS)})")
    if not character.has_ref("master"):
        raise CharacterBibleError(f"{character.name}: approve the master reference before drawing a {kind}")

    base_kind, base_item = "master", None
    if kind == "turnaround":
        if item:
            raise CharacterBibleError("a turnaround reference takes no item")
        outfit_id = character.default_outfit
        lead = f"Image 1 is the approved character reference for {character.name}."
        body = (
            f"Create a character turnaround sheet of exactly this character: front view, three-quarter view, "
            f"side profile and back view, full body, standing side by side and evenly spaced, {background}. "
            f"{lock_clause(character)}"
        )
    elif kind == "outfit":
        if not item:
            raise CharacterBibleError("an outfit reference needs an outfit id")
        outfit_id = character.outfit_id(item)
        if outfit_id == character.default_outfit:
            warnings.append(f"'{item}' is the default outfit, which the master already shows")
        lead = f"Image 1 is the character reference for {character.name}."
        body = (
            f"{lock_clause(character, include_outfit=False)} Change only the clothes to: "
            f"{character.outfit(outfit_id)['description']}. Full body, standing and facing the camera, "
            f"arms relaxed at the sides, {background}."
        )
    else:
        if not item:
            raise CharacterBibleError(f"a {kind} reference needs a {kind} id")
        outfit_id = character.outfit_id(outfit)
        if outfit_id != character.default_outfit:
            if not character.has_ref("outfit", outfit_id):
                raise CharacterBibleError(
                    f"{character.name}: approve the '{outfit_id}' outfit reference before drawing a {kind} in it"
                )
            base_kind, base_item = "outfit", outfit_id
        lead = f"Image 1 is the character reference for {character.name}."
        if kind == "pose":
            body = (
                f"{lock_clause(character, outfit_id)} Same character in the same outfit, full body, new pose: "
                f"{character.pose_text(item).rstrip('.')}. {background}."
            )
        else:
            body = (
                f"{lock_clause(character, outfit_id)} Head-and-shoulders portrait facing the camera, expression: "
                f"{character.expression_text(item).rstrip('.')}. {background}."
            )

    base = character.ref_path(base_kind, base_item)
    _check_identity(character, base_kind, base_item, False, warnings)
    prompt = " ".join(p for p in (lead, body, _sentence(cast.style_line), no_text) if p)
    return {
        "mode": "reference",
        "kind": kind,
        "item": item,
        "outfit": outfit_id,
        "prompt": prompt,
        "image_paths": [str(base)],
        "legend": [{"index": 1, "kind": "identity", "character": character.id, "path": str(base)}],
        "aspect_ratio": aspect,
        "model": s["models"]["reference"],
        "preferred_provider": "fal",
        "target": str(character.ref_path(kind, item)),
        "warnings": warnings,
    }


def build_variant(
    base_image: str | Path,
    change: str,
    *,
    aspect_ratio: Optional[str] = None,
    cast: Optional[Cast] = None,
) -> dict[str, Any]:
    """A change-one-thing variant of an approved still (blink, tear, mouth open mid-word)."""
    settings = cast.settings if cast else DEFAULT_SETTINGS
    prompt = (
        "Keep image 1 exactly the same: the same characters, faces, clothes, composition, camera angle, lighting "
        f"and style. Change only this: {change.strip().rstrip('.')}. {settings['no_text_clause']}"
    )
    return {
        "mode": "reference",
        "kind": "variant",
        "prompt": prompt,
        "image_paths": [str(base_image)],
        "legend": [{"index": 1, "kind": "base", "character": None, "path": str(base_image)}],
        "aspect_ratio": aspect_ratio,
        "model": settings["models"]["reference"],
        "preferred_provider": "fal",
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Approving references
# ---------------------------------------------------------------------------


def _save_ref_jpeg(source: Path, target: Path) -> None:
    from PIL import Image

    with Image.open(source) as image:
        if image.mode in ("RGBA", "LA", "P"):
            rgba = image.convert("RGBA")
            flat = Image.new("RGB", rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.split()[-1])
            image = flat
        else:
            image = image.convert("RGB")
        image.thumbnail((REF_MAX_SIDE, REF_MAX_SIDE))
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, "JPEG", quality=REF_JPEG_QUALITY)


def _archive(character: Character, path: Path, stamp: str) -> None:
    if not path.exists():
        return
    archive = character.root / REFS_DIRNAME / SUPERSEDED_DIRNAME
    archive.mkdir(parents=True, exist_ok=True)
    flat_name = path.relative_to(character.root / REFS_DIRNAME).as_posix().replace("/", "-")
    shutil.move(str(path), str(archive / f"{stamp}-{flat_name}"))


def approve_ref(
    cast: Cast,
    character_id: str,
    kind: str,
    candidate: str | Path,
    *,
    item: Optional[str] = None,
    outfit: Optional[str] = None,
    provenance: Optional[dict[str, Any]] = None,
    replace: bool = False,
) -> Path:
    """Save a user-approved candidate as a bible reference, with a provenance sidecar.

    The image is stored as JPEG (long side <= 1536 px) at the conventional path.
    An existing reference is kept unless replace=True, which moves it (and its
    sidecar) to refs/_superseded/ rather than deleting it.
    """
    character = cast.character(character_id)
    candidate = Path(candidate)
    if not candidate.exists():
        raise CharacterBibleError(f"candidate image not found: {candidate}")
    if kind not in REF_KINDS:
        raise CharacterBibleError(f"unknown reference kind '{kind}' (use one of {', '.join(REF_KINDS)})")

    if kind in ("master", "turnaround"):
        if item:
            raise CharacterBibleError(f"a {kind} reference takes no item")
        outfit_id = character.default_outfit
    elif kind == "outfit":
        outfit_id = character.outfit_id(item)
    else:
        if not item:
            raise CharacterBibleError(f"a {kind} reference needs a {kind} id")
        (character.pose_text if kind == "pose" else character.expression_text)(item)
        outfit_id = character.outfit_id(outfit)
    if kind != "master" and not character.has_ref("master"):
        raise CharacterBibleError(f"{character.name}: approve the master reference first")

    target = character.ref_path(kind, item)
    sidecar = character.sidecar_path(kind, item)
    if target.exists():
        if not replace:
            raise CharacterBibleError(f"{target} is already approved; pass replace=True to supersede it")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        _archive(character, target, stamp)
        _archive(character, sidecar, stamp)

    _save_ref_jpeg(candidate, target)
    record = {
        **(provenance or {}),
        "character": character.id,
        "kind": kind,
        "item": item,
        "outfit": outfit_id,
        "file": target.name,
        "approved_on": datetime.now().date().isoformat(),
        "candidate_file": str(candidate),
        "identity_hash": character.identity_hash(),
        "item_hash": character.item_hash(kind, item, outfit_id),
    }
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return target


def rehash(cast: Cast, character_id: str) -> list[Path]:
    """Re-stamp a character's sidecars with the current text hashes.

    Only after a human has confirmed the approved images still match the
    edited text (a typo fix, a clarified wording). A real change to the look
    needs new references instead.
    """
    character = cast.character(character_id)
    updated = []
    for sidecar in sorted((character.root / REFS_DIRNAME).rglob("*.json")):
        if SUPERSEDED_DIRNAME in sidecar.parts:
            continue
        with open(sidecar, encoding="utf-8") as f:
            record = json.load(f)
        kind, item = record.get("kind"), record.get("item")
        outfit = record.get("outfit") or character.default_outfit
        record["identity_hash"] = character.identity_hash()
        record["item_hash"] = character.item_hash(kind, item, character.outfit_id(outfit))
        record["rehashed_on"] = datetime.now().date().isoformat()
        with open(sidecar, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        updated.append(sidecar)
    return updated


def cast_status(cast: Cast) -> dict[str, Any]:
    """What each character has approved, what is missing, and what is stale."""
    report: dict[str, Any] = {}
    for character in cast.characters.values():
        warnings = []
        master = character.ref_state("master")
        if character.data["status"] == "locked" and master == "missing":
            warnings.append("status is locked but there is no approved master reference")
        if character.data["status"] == "draft" and master in ("approved", "unverified"):
            warnings.append("the master is approved; set status: locked and locked_on in character.yaml")
        variant_of = character.data.get("variant_of")
        if variant_of and variant_of not in cast.characters:
            warnings.append(f"variant_of '{variant_of}' is not in this cast")
        for other in (character.data.get("relationships") or {}):
            if other not in cast.characters:
                warnings.append(f"relationship to '{other}', who is not in this cast")
        report[character.id] = {
            "name": character.name,
            "role": character.data["role"],
            "status": character.data["status"],
            "scope": character.scope,
            "master": master,
            "turnaround": character.ref_state("turnaround"),
            "outfits": {o: character.ref_state("outfit", o) for o in character.data["wardrobe"]["outfits"]
                        if o != character.default_outfit},
            "poses": {p: character.ref_state("pose", p) for p in character.data.get("poses") or {}},
            "expressions": {e: character.ref_state("expression", e) for e in character.data.get("expressions") or {}},
            "warnings": warnings,
        }
    return report


def contact_sheet(
    paths: list[str | Path],
    output: str | Path,
    *,
    labels: Optional[list[str]] = None,
    columns: int = 4,
    thumb: int = 384,
) -> Path:
    """Tile candidate images into one labelled JPEG so the user can pick at a glance."""
    from PIL import Image, ImageDraw, ImageFont

    if not paths:
        raise CharacterBibleError("contact_sheet needs at least one image")
    labels = labels or [Path(p).stem for p in paths]
    columns = max(1, min(columns, len(paths)))
    rows = (len(paths) + columns - 1) // columns
    label_h = 28
    sheet = Image.new("RGB", (columns * thumb, rows * (thumb + label_h)), (32, 32, 32))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (path, label) in enumerate(zip(paths, labels)):
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((thumb, thumb))
            x = (index % columns) * thumb
            y = (index // columns) * (thumb + label_h)
            sheet.paste(image, (x + (thumb - image.width) // 2, y + (thumb - image.height) // 2))
            draw.text((x + 8, y + thumb + 6), f"{index + 1}. {label}", fill=(235, 235, 235), font=font)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "JPEG", quality=90)
    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cast_from_args(args: argparse.Namespace) -> Cast:
    if args.cast_dir:
        playbook = None
        if args.playbook:
            from styles.playbook_loader import load_playbook

            playbook = load_playbook(args.playbook)
        story = [PROJECTS_DIR / args.project / "cast"] if args.project else []
        return load_cast_from_dir(
            Path(args.cast_dir), playbook=playbook, story_dirs=story, include_underscored=args.include_examples
        )
    if not args.channel:
        raise CharacterBibleError("pass --channel <id> (or --cast-dir <path> --playbook <name>)")
    return load_cast(args.channel, args.project, include_underscored=args.include_examples)


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv: Optional[list[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Devanagari names on Windows consoles
    except (AttributeError, ValueError):
        pass

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--channel", help="channel id (uses its visuals.cast_dir and playbook)")
    common.add_argument("--project", help="project id whose cast/ holds story-only characters")
    common.add_argument("--cast-dir", help="load this cast folder directly instead of a channel's")
    common.add_argument("--playbook", help="style playbook for --cast-dir")
    common.add_argument("--include-examples", action="store_true", help="also load '_'-prefixed example folders")

    parser = argparse.ArgumentParser(prog="python -m lib.character_bible", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", parents=[common], help="list the cast")
    sub.add_parser("status", parents=[common], help="approved / missing / stale references per character")
    show = sub.add_parser("show", parents=[common], help="a character's canonical text and references")
    show.add_argument("character")
    show.add_argument("--outfit")
    shot = sub.add_parser("shot", parents=[common], help="build a shot request from a JSON spec (shot or scene)")
    shot.add_argument("--spec", required=True, help="JSON file: a shot spec, or a scene_plan scene")
    shot.add_argument("--aspect", default="16:9")
    shot.add_argument("--format", dest="video_format", choices=["long_form", "shorts"])
    shot.add_argument("--mode", default="reference", choices=["reference", "text"])
    shot.add_argument("--allow-stale", action="store_true")
    job = sub.add_parser("refjob", parents=[common], help="build the request that draws one bible reference")
    job.add_argument("character")
    job.add_argument("kind", choices=REF_KINDS)
    job.add_argument("item", nargs="?")
    job.add_argument("--outfit")
    approve = sub.add_parser("approve", parents=[common], help="save an approved candidate as a reference")
    approve.add_argument("character")
    approve.add_argument("kind", choices=REF_KINDS)
    approve.add_argument("item", nargs="?")
    approve.add_argument("--file", required=True, help="the approved candidate image")
    approve.add_argument("--outfit")
    approve.add_argument("--provenance", help="JSON file: model, prompt, input refs, cost_usd, source_project")
    approve.add_argument("--replace", action="store_true")
    rh = sub.add_parser("rehash", parents=[common], help="accept a cosmetic text edit for a character's references")
    rh.add_argument("character")
    sheet = sub.add_parser("sheet", help="tile candidate images into a labelled contact sheet")
    sheet.add_argument("--out", required=True)
    sheet.add_argument("--columns", type=int, default=4)
    sheet.add_argument("images", nargs="+")

    args = parser.parse_args(argv)
    try:
        if args.command == "sheet":
            print(contact_sheet(args.images, args.out, columns=args.columns))
            return 0
        cast = _cast_from_args(args)
        if args.command == "list":
            _print_json({c.id: {"name": c.name, "role": c.data["role"], "status": c.data["status"],
                                "scope": c.scope} for c in cast.characters.values()})
        elif args.command == "status":
            _print_json(cast_status(cast))
        elif args.command == "show":
            character = cast.character(args.character)
            _print_json({
                "identity_text": identity_text(character, args.outfit),
                "lock_clause": lock_clause(character, args.outfit),
                "references": cast_status(cast)[character.id],
            })
        elif args.command == "shot":
            with open(args.spec, encoding="utf-8") as f:
                spec = json.load(f)
            if "character_actions" in spec or "start_seconds" in spec:
                spec = shot_from_scene(spec)
            _print_json(build_shot(cast, spec, aspect_ratio=args.aspect, video_format=args.video_format,
                                   mode=args.mode, allow_stale=args.allow_stale))
        elif args.command == "refjob":
            _print_json(build_ref_job(cast, args.character, args.kind, args.item, outfit=args.outfit))
        elif args.command == "approve":
            provenance = None
            if args.provenance:
                with open(args.provenance, encoding="utf-8") as f:
                    provenance = json.load(f)
            print(approve_ref(cast, args.character, args.kind, args.file, item=args.item, outfit=args.outfit,
                              provenance=provenance, replace=args.replace))
        elif args.command == "rehash":
            for path in rehash(cast, args.character):
                print(path)
    except CharacterBibleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
