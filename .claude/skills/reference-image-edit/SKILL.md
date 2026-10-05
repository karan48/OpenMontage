---
name: reference-image-edit
description: Reference-conditioned image generation on fal.ai with Meta Muse Image Edit (meta/muse-image/edit, 1-10 reference images, $0.01/image) and FLUX.1 Kontext [pro] (fal-ai/flux-pro/kontext, one reference). Use when drawing a known character in a new scene from approved reference images, building a character bible (turnaround, outfits, poses, expressions from a master), making change-one-thing variants of a still, or removing stray lettering. Covers inputs, limits, prompt patterns that held identity, and the failure modes seen in production. Tool - fal_reference_image.
metadata:
  author: OpenMontage
  version: "1.0.0"
  tags: fal, muse, kontext, reference-image, character-consistency, image-edit
---

# Reference Image Edit (fal: Meta Muse, FLUX Kontext)

Text-only models redraw a character from words every time, so faces drift and two-shots swap clothes. A reference model **copies the identity from an image** and takes the new scene from the prompt. OpenMontage calls these models through the `fal_reference_image` tool. The prompts and ordered reference lists normally come from `lib/character_bible.py`, and the workflow lives in `skills/meta/character-bible.md`.

## Models

| | Meta Muse Image Edit | FLUX.1 Kontext [pro] |
|---|---|---|
| Endpoint | `meta/muse-image/edit` (no `fal-ai/` prefix) | `fal-ai/flux-pro/kontext` |
| References | 1-10 (`image_urls`, HTTP(S) or data URLs) | exactly 1 (`image_url`) |
| Seed | **none**: outputs are not reproducible | yes |
| Aspect ratio | any `W:H` from 1:16 to 16:1; rendered at a fixed ~2.5 MP (9:16 → 1152×2048) | `aspect_ratio` presets |
| Other inputs | `num_images` 1-10, `output_format` jpeg/png/webp (default webp), `sync_mode` | `guidance_scale` (3.5), `output_format` jpeg/png |
| Negative prompt | none: write bans as plain instructions | none |
| List price (2026-10-04) | **$0.01 / image** | $0.04 / image |
| Proven on | 47 Drafts: 14 picks, incl. a two-shot with no wardrobe swap | 47 Drafts: Aarav's 4 solo shots |

Check the live price before a batch (fal MCP `get_pricing`). Prices change without notice. Muse is the default. Switching to Kontext is a model switch, so ask the user first.

## Prompt structure that held identity

Order matters. This is the structure of the approved 47 Drafts prompts:

1. **Legend first.** One sentence per reference image, in input order: "Image 1 is the character reference for Riya." / "Image 2 shows Riya's body pose; use it for the pose only."
2. **Lock clause.** "Keep Riya's exact face, eyes, eyebrows, skin tone, long voluminous dark-brown wavy hair, small gold hoop earrings and coral knit sweater." Name the hair, accessories and outfit with the same words every time.
3. **Ignore the noise** in the reference: "Ignore the collage elements in image 1 (polaroid photo, white paper scraps, paint strokes, the book)." For plain-background bible refs: "Ignore the plain backgrounds of the character reference images."
4. **"New scene, <aspect> <framing>:"** then the scene: setting, action, emotion, light, time of day.
5. **Style line**, then the **no-text clause** last: "No text, no letters, no numbers, no signs, no logos, no watermark."

Approved example (sc18, 9:16, $0.01):

> Image 1 is the character reference for Riya: keep her exact face, eyes, eyebrows, skin tone, long voluminous dark-brown wavy hair, small gold hoop earrings and coral knit sweater. Ignore the collage elements in image 1 (polaroid photo, white paper scraps, paint strokes, the book). New scene, vertical 9:16 close-up: Riya standing on a crowded Indian railway platform in the morning, smiling with wet, glistening eyes, holding back tears she won't let fall. Golden-amber morning light through the platform canopy falls on her face; the train and platform are softly blurred behind her (shallow depth of field, light rays). Her face sits in the upper third of the frame. Warm painterly modern anime illustration, glowing light, textured brush strokes. No text, no letters, no numbers, no signs, no logos, no watermark.

## Patterns

- **Two-shot.** Give one identity reference per character, and say who is where: "Image 1 is Riya and image 2 is Aarav: keep each one's exact face, hair and outfit… Riya on the left and Aarav on the right… Do not swap their clothes." (sc02: no swap.)
- **Wide from an approved close-up.** Pass the identity reference plus the approved close-up of the same moment: "Image 2 is a medium close-up of the moment to show. Create the WIDE SHOT of this same moment: …" (sc06_a matched sc06_b for the crossfade.) This only works because image 2 was itself drawn from the current reference.
- **Bible jobs from the master.** Turnaround, outfit, pose and expression references are each drawn from the approved master on a plain grey background, so every image the model ever sees shows the same person.
- **Change-one-thing variant.** "Keep image 1 exactly the same: the same characters, faces, clothes, composition, camera angle, lighting and style. Change only this: her eyes closed mid-blink." Muse is built for small, precise edits. Use this for `anime_scene` crossfades (blink, tear, mouth open mid-line).
- **Cleanup pass.** For stray lettering, run a single-image edit: "Remove all the small text, captions and printed lettering from the posters on the wall… keep everything else exactly unchanged." ($0.01; sc09 and sc11 were fixed this way.)

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| The old face comes back | A reference showed an **older version** of the character (the "ref + old frame" redraw, sc18_mA1, rejected) | Never pass a frame of another person or an older version. Only frames drawn from the current refs are allowed as continuity |
| Bright daytime at a 4 AM beat | The time of day was implied, not stated (sc14_mB1) | Spell out the sky: "sky still dark navy night with fading stars, a thin band of pale blue on the horizon, city lights on" |
| Lettering on posters, signs, train coaches | Busy backgrounds invite text | "posters showing only pictures", "plain coach with no writing", then a cleanup pass |
| HTTP 422 `content_policy_violation` | The prompt or a reference tripped the filter (**not billed**) | Rephrase the scene neutrally and retry once. If it repeats, check the reference image |
| Night shots too dark (Kontext) | Low-key lighting | "bright phone glow, face fully visible"; lift with ffmpeg `eq` if needed |
| An output you liked can't be reproduced | Muse has no seed | Keep every output on disk and log its prompt and refs |

## Sizes and formats

- Muse renders ~2.5 MP whatever ratio you pass, and its PNGs are ~3 MB. Ask for `output_format: jpeg` unless you need transparency.
- The tool shrinks local references over 2 MB or 1536 px to JPEG before upload. Approved bible references are already stored as JPEG at ≤1536 px.

## Sources

- fal model schema for `meta/muse-image/edit` and live pricing for both endpoints (fal MCP, 2026-10-04).
- `projects/young-story-short-01/assets/images/muse/generation_log.json` and `decision_log.json` (47 Drafts, 2026-10-03/04): every prompt, reference list, verdict and cost.
