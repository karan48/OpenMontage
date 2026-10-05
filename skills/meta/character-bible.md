# Character Bible - Meta Skill

## When to Use

Use this whenever a **named character appears in more than one shot, or speaks**: animated stories, drama, recurring hosts and personas.

- **`scene_plan` stage, `cast` sub-stage:** after the script is approved and before shots are planned, make sure every character the story needs is in the bible, with the references the scenes need.
- **`assets` stage:** every shot that shows a bible character is built from the bible.
- **Any time** the user asks to create, change or reuse a character.

Channels with `visuals.cast_dir` always use it. Any other channel can adopt it by copying `channels/_template/cast/` and setting `visuals.cast_dir`.

## Why

Text-only image models redraw a character from words every time. On 47 Drafts (`projects/young-story-short-01`), pasting a locked description into `flux/schnell` still drifted faces between shots, and two-shots swapped the two characters' clothes (0/5 usable). A reference model (Meta Muse edit, $0.01/image) that **copies identity from an approved image** fixed both.

The bible makes that repeatable. The look is written once, approved images are stored beside it, and **code assembles every prompt and reference list**. Appearance text is never retyped, so it can't drift.

## The chain

```
Character (text)  ->  Master  ->  Turnaround / Outfits  ->  Poses  ->  Expressions  ->  Scenes
character.yaml        refs/        refs/turnaround.jpg       refs/      refs/           build_shot()
(user approves)       master.jpg   refs/outfits/<id>.jpg     poses/     expressions/    per scene
```

| Step | Model (tool) | Cost | Gate |
|---|---|---|---|
| Character text | none | free | user approves the text |
| Master: 4 candidates, user picks one | `flux/schnell` (`flux_image` via `image_selector`) | ~$0.003 each | user picks |
| Turnaround, outfits | Muse edit (`fal_reference_image`), drawn from the master | $0.01 each | user approves |
| Poses, expressions the script needs | Muse edit, drawn from the master (or the outfit ref) | $0.01 each | user approves |
| Scene stills | Muse edit with the bible references | $0.01 each | the `assets` gate |
| Variants (blink, tear, mouth open) | Muse edit from the approved still | $0.01 each | `assets` gate |

A full character with a turnaround, 2 outfits, ~6 poses and ~8 expressions costs about **$0.15-0.25**. Check live prices with the fal MCP `get_pricing` before a batch, and announce each paid call as the Decision Communication Contract requires.

## Files

```
channels/<id>/cast/                      # recurring cast (committed)
  cast.yaml                              # style line, no-text clause, models, reference policy, format hints
  <character-id>/
    character.yaml                       # locked TEXT. People edit it with the Edit tool; code never rewrites it
    refs/master.jpg + master.json        # approved image + provenance sidecar
    refs/turnaround.jpg, refs/outfits/<id>.jpg, refs/poses/<id>.jpg, refs/expressions/<id>.jpg
    refs/_superseded/                    # replaced references, kept forever
projects/<project-id>/cast/<character-id>/   # story-only characters, same format
```

- **What "approved" means:** the image exists at its conventional path. The sidecar records model, prompt, input refs, cost, date, source project, the outfit, and hashes of the text it was drawn from.
- **Stale references:** if `identity` (or that item's pose, expression or outfit text) changes after approval, the reference reports **stale**. `build_shot` refuses a stale identity and skips a stale pose or expression image.
- **Schemas:** `schemas/channels/character.schema.json` and `schemas/channels/cast.schema.json`. A template character is in `channels/_template/cast/_example/character.yaml`.
- **Library and CLI:** `lib/character_bible.py`. Every command takes `--channel <id>` and, for story casts, `--project <id>`:

```bash
python -m lib.character_bible status  --channel <channel> --project <p>    # approved / missing / stale
python -m lib.character_bible show    --channel <channel> <id> [--outfit wedding]
python -m lib.character_bible refjob  --channel <channel> <id> master|turnaround|outfit|pose|expression [item] [--outfit o]
python -m lib.character_bible shot    --channel <channel> --project <p> --spec scene.json --aspect 16:9 --format long_form
python -m lib.character_bible approve --channel <channel> <id> pose doorway --file <candidate> --provenance prov.json
python -m lib.character_bible sheet   --out <contact.jpg> <img1> <img2> ...
```

## Process

### 1. Cast the story (`scene_plan.cast` sub-stage)

1. From the approved script, list every **speaking or recurring** character, plus the outfits, poses and expressions the scenes will need. Background extras with no lines and one appearance don't need entries; describe them in the scene text.
2. Run `status`. Reuse every existing character exactly as locked. Never redesign a locked character for one story.
3. For a new character, draft `character.yaml` from the template:
   - Put a recurring character in the channel `cast/`, and a one-story character in `projects/<p>/cast/`.
   - Fill `identity` with concrete, visual words (face shape, eyes, hair length, colour and style, skin tone, build, one or two marks, everyday accessories).
   - Give the default outfit a `short` form, and add only the outfits, poses and expressions this story needs.
4. Present the text and get approval. This step is free.
5. Set the sub-stage context `story_has_characters`, and log `category: "character_bible"` decisions (below).

### 2. Master reference (gate)

1. `refjob <id> master` returns a text-to-image request with `num_candidates`.
2. Generate that many candidates through `image_selector` with `preferred_provider: "flux"`, a different `seed` each, `output_path` under `projects/<p>/assets/images/cast/<id>/master/`.
3. `sheet` them into one contact sheet. Present it and **end the turn**.
4. When the user picks one, run `approve <id> master --file <pick> --provenance <json>`. Then set `status: locked` and `locked_on` in `character.yaml` with the Edit tool.
- **User-supplied art** (a reference sheet they made) can be approved as the master directly, with provenance `{"source": "user"}`. If the sheet is busy (labels, collage, several views), add `ref_notes` saying what to ignore.
- **Weak `flux/schnell` candidates:** propose `flux-pro` (~$0.05) with a cost note. That's a model switch, so ask first.

### 3. Turnaround, outfits, poses, expressions (gate)

1. Run `refjob` for each item the story needs. Every request uses the approved master as image 1. A pose or expression in a non-default outfit uses that outfit's approved reference instead, so approve outfits first.
2. Generate one image per item with `image_selector` (`preferred_provider: "fal"`), plus a contact sheet. Present it and **end the turn**.
3. `approve` each pick. Redo only the rejected ones.
- Build the library **story by story**. Generate what the approved scene plan uses, not a speculative full set.

### 4. Scene generation (`assets` stage)

For each scene, build the request from the bible:

```python
from lib.character_bible import load_cast, build_scene
from tools.tool_registry import registry

registry.discover()
cast = load_cast("<channel>", project_id="<project-id>")
req = build_scene(cast, scene, aspect_ratio="16:9", video_format="long_form")   # scene = a scene_plan scene
for warning in req["warnings"]:
    print("WARN:", warning)                     # surface every warning to the user
inputs = {k: req[k] for k in ("prompt", "image_paths", "aspect_ratio", "model", "preferred_provider") if req.get(k)}
if req["mode"] == "text":                       # a plate with no bible character
    inputs.update(negative_prompt=req["negative_prompt"], width=req["width"], height=req["height"])
inputs["output_path"] = f"projects/<project-id>/assets/images/scenes/{scene['id']}_1.jpg"
result = registry.get("image_selector").execute(inputs)
```

- **Scene descriptions name characters, never describe them.** "Meera stands in the doorway, the letter in her hand", never "Meera, in a green saree…". The look comes from the bible, and the outfit from `character_actions[].outfit`.
- **Fill `character_actions` for every character in the frame:** `character_id`, `action_sequence`, plus optional `pose`, `expression`, `outfit` and `frame_position`. `frame_position` is required in practice for two-shots.
- **Keep every output.** Muse has no seed. Log each attempt (file, prompt, refs, verdict, cost) in `assets/images/<batch>/generation_log.json`.
- **Variants** for `anime_scene` crossfades use `build_variant(approved_still, "her eyes closed mid-blink", cast=cast)`. Time them to the spoken word with the cut's `cues` (forced-alignment onsets; see "Word-timed variants" in `skills/pipelines/animation/compose-director.md`).
- **Hero clips** (AI image-to-video) start only from the **approved still** of that shot. They are approval-gated per the channel's `visuals.hero_clips` rule. Never use text-to-video for a bible character.

### 5. QA: every frame that shows a character

- **Side by side with the master:** face shape, eyes, hair (length, colour, style), skin tone, marks, accessories, build and apparent age.
- **Outfit:** it matches the shot's outfit. In two-shots, nobody wears someone else's clothes.
- **Hands and limbs:** no extra fingers, no merged hands.
- **No AI lettering or watermarks.** Fix them with a cleanup pass (`reference-image-edit` skill).
- **Policies:** the channel's policies hold (modesty, no graphic harm).
- **Composition:** Shorts safe zones are respected, and the time of day and light match the script.

### 6. When a frame drifts

1. Regenerate the same request, up to 2 more tries. Outputs vary without a seed.
2. Add the approved pose or expression image (set `reference_policy` for this shot, or attach it explicitly), and tighten the scene text.
3. Propose the fallback model (`fal-ai/flux-pro/kontext`, $0.04, one reference). That's a model switch, so ask first.
4. Never reword the canonical text to rescue one image. That breaks every other shot.

## Changing a locked character

- **A cosmetic edit** (typo, clearer wording) leaves the look unchanged. After the user confirms the images still match, run `python -m lib.character_bible rehash --channel <id> <char>`.
- **A real change** (new hairstyle, different age) needs new references: `approve … --replace` archives the old ones in `refs/_superseded/`. Images made before the change are stale for reuse.
- **A time jump** (the same person 20 years younger) is a **new character** with `variant_of: <id>`, not an edit.

## Promoting a story character

When a story character returns, move its folder from `projects/<p>/cast/` to the channel `cast/`. The sidecars keep `source_project`. Add a row to the channel's `characters.md` index.

## Reference policy and the first pilot

`cast.yaml` sets which images go into each shot:

- **Identity:** the master, one per character, always.
- **Pose:** the approved pose image, only when its outfit matches the shot.
- **Expression:** the approved expression image, on close-ups.
- **Continuity:** an earlier frame of the same scene, only if it was drawn from the current refs.

Over the model's cap (10 for Muse), continuity drops first, then the turnaround, expression and pose. Identity is never dropped.

On a channel's first story, A/B two shots (identity only vs identity + pose + expression), show the user, and lock the winner in `cast.yaml`.

## Logging

| Event | `decision_log` entry |
|---|---|
| Character text approved | `category: "character_bible"`, `subject: "<Name> character design"` |
| Master or other reference approved | `category: "character_bible"`, `subject: "<Name> <kind> reference"` (same subject when replaced) |
| Reference model chosen or switched | `category: "provider_selection"`, `subject: "Character shot model"` |
| Reference policy locked | `category: "character_bible"`, `subject: "Reference policy"` |

## Rules

- **The bible is the only source of a character's look.** Never paste or paraphrase appearance text into a scene description.
- **Never feed the model an image of another person, or of an older version of the character.** In 47 Drafts, a frame with the old face brought the old face back.
- **Never delete an approved reference.** Replace with `--replace`, which archives the old file.
- **Code never rewrites `character.yaml`.** People edit it with the Edit tool, written as UTF-8. Never edit it with PowerShell `Set-Content`.
- **A profile supplies defaults, never permission.** Each generation step is announced with its model and cost, and gated by the user.
