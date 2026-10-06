# Channel Profiles - Meta Skill

## When to Use

Use this at the start of **every production request**, before Rule Zero's pipeline selection.

The user runs several YouTube channels, each with its own language, format, voice, script style and look. `channels/<id>/` holds each channel's standing defaults. Without a profile, every video falls back to one global set of defaults, and a Hinglish product-review Short ends up with the Hindi long-form explainer's voice and structure.

## What a Profile Holds

| File | Contains | Read at |
|---|---|---|
| `channels/<id>/channel.yaml` | Language; `formats` (`long_form` and/or `shorts`, each with aspect ratio, media profile, target length, structure, composition mode, optional pipeline override, Shorts sources, pacing); pipeline (plus alternates), style playbook, runtime recommendation; narration (provider, model, voice_id, settings, planning wpm, register); humor level; visual approach and sourcing; music; publishing; policies; `open_questions` | Intake and proposal, then every stage |
| `channels/<id>/script-guide.md` | The channel's register, hooks, humor and "never" list, plus **a structure section per format**, with example lines | Script stage, after `skills/creative/storytelling.md` |
| `channels/<id>/characters.md` (optional) | Locked recurring cast: appearance blocks, LoRA, voices, reuse rules | Scene and asset stages, plus character design |
| `channels/<id>/cast/` (optional, `visuals.cast_dir`) | **Structured character bible**: `cast.yaml` plus one folder per character, each with `character.yaml` (locked text) and `refs/` (approved master, turnaround, outfits, poses, expressions). Prompts are built from it by `lib/character_bible.py`; see `skills/meta/character-bible.md` | `scene_plan` (`cast` sub-stage) and `assets` |
| `channels/<id>/brand/` (optional, `brand` in `channel.yaml`) | **Locked brand assets**: the logo (plus a circle-masked PNG), the channel intro clip and its sting, the intro's Remotion source and a README with the re-render recipe. `load_channel` fails if a file the `brand` block names is missing | Script, scene plan, assets, edit/compose and publish (see "Brand intro and standing structure") |

Load and validate with the loader. Don't read the YAML by hand:

```bash
python -c "from lib.channel_profile import list_channels; print(list_channels())"
python -c "from lib.channel_profile import load_channel; import json; print(json.dumps(load_channel('<id>'), indent=2, ensure_ascii=False))"
# One format with channel defaults filled in (always includes the resolved pipeline):
python -c "from lib.channel_profile import load_channel, resolve_format; import json; print(json.dumps(resolve_format(load_channel('<id>'), '<long_form|shorts>'), indent=2, ensure_ascii=False))"
```

`load_channel` fails loudly if the profile, its playbook, pipelines, media profile or referenced files are missing. Surface that as a blocker. Never proceed on a guessed profile.

## Process

### 1. Identify the Channel

- **The user names it** ("for my review channel", "Rani ka next reel"): map the name to an id from `list_channels()`.
- **The topic or format implies one, but the user didn't say**: ask with `AskUserQuestion`, listing the channels and recommending the likely one first. Never pick silently. A wrong channel means the wrong language, voice and aspect ratio for the whole run.
- **No channel fits** (a one-off, a client video, an experiment): proceed without a profile, say so, and don't pass `channel=` to `init_project`.
- **The request fits a channel that doesn't exist yet**: offer to create one from `channels/_template/` (see "Add a Channel" below).

### 2. Identify the Format

Most channels publish both **long-form** (16:9) and **Shorts** (9:16). Settle which one this production is:

- **The user says it** ("a Short", "full video", "reel", "10-minute"): use it.
- **Unclear**: ask, offering the channel's `formats`. Never default silently. The format changes the aspect ratio, length, structure and often the build mode.
- **A Shorts cut-down from an existing long video** (`sources` includes `cut_down`): it is its own production with `video_format='shorts'`. Read the long video's project as the source, reuse its approved assets, and follow the script guide's cut-down rules.

`resolve_format(profile, video_format)` returns that format's settings, with `pipeline` resolved from the format override or the channel default.

### 3. Initialize the Project with the Channel and Format

```bash
python -c "from lib.checkpoint import init_project; init_project('<project-id>', title='<Title>', pipeline_type='<pipeline>', style_playbook='<playbook>', channel='<channel-id>', video_format='<long_form|shorts>')"
```

This writes `channel` and `video_format` into `project.json`. Also put `metadata.channel` and `metadata.video_format` on the `brief` and `proposal_packet`. Their top-level schemas are closed, and `metadata` is the free-form slot for them.

Log both choices in `decision_log` with `category: "channel_selection"`. Use subject `"Channel"` with the other channels in `options_considered`, and subject `"Video format"` with the other format. Give the reason for each (the user named it / topic fit / user confirmed).

### 4. Pre-fill Each Stage

The profile supplies the recommendation. The stage director still runs its normal process. "The format" below means `resolve_format(profile, video_format)`.

| Stage | What the profile seeds |
|---|---|
| **Pipeline selection** | The format's `pipeline`. Use an `alternate_pipelines` entry when its situation applies (e.g. product-review `no_footage` → `animated-explainer`, `app_review` → `screen-demo`). Mention it when the pipeline is beta. |
| **Proposal** | `production_plan.playbook` ← `style_playbook`. `voice_selection.provider` / `voice_id` ← `narration`. `composition_mode` ← the format's `composition_mode`. `render_runtime` ← `render_runtime_recommendation`. `music_source` ← `music.source_order`. Aspect ratio and duration ← the format. Raise every `open_questions` item that affects this video, and ask; don't assume. |
| **Script** | Read `script-guide.md` after `storytelling.md`, and use **the section for this format**. The guide wins on register, structure and humor level (`script.humor`). Plain-language rules stay universal. Time sections with `narration.planning_wpm` against the format's `target_seconds`, write in `language.script` convention, and use `narration.delivery_markup`. Put model, stability and similar settings into `script.voice_performance.provider_notes`. |
| **Scene plan / assets** | With a `cast_dir`: cast the story and build every character shot from the bible (`skills/meta/character-bible.md`). Never paste appearance text by hand. Use `visuals.character_image_model` for character shots, and follow `visuals.hero_clips` for AI video. Without one: paste `characters.md` blocks verbatim into prompts. Follow `visuals.sourcing` and `visuals.image_model`, and the format's `pacing`. State the format's aspect ratio in every image prompt, because playbook prefixes are format-neutral. Honour `visuals.ai_video` (`approval_gated` = propose with a cost estimate, then wait for an explicit yes per use). Apply every `policies` entry. Pass `narration.*` settings to `tts_selector` (`preferred_provider`, `voice_id`, `model_id`, `stability`, `similarity_boost`, `speed`). |
| **Edit / compose** | The format's `media_profile` and `aspect_ratio` set the render size. In 9:16, keep text out of the Shorts UI zones (bottom 20% and right 15%). |
| **Publish** | The `publishing` block (title language, thumbnail direction, disclosures, closing question, pinned comment, comment moderation, sources), plus the format's `cross_post` if set. |
| **Brand intro** | If the profile has a `brand` block, its intro belongs to every production in the formats it lists — see below. |

#### Brand intro and standing structure

A channel's `brand.intro` is a **locked brand asset**, like a logo file, not a creative scene. Never restyle, regenerate, re-time or swap it for a template per video. Stage by stage:

- **Script:** reserve the gap. Set `delivery_cues.pause_after_seconds` on the section that ends the opening promise to the intro's `seconds`, and record `metadata.channel_intro = {after_section, seconds, asset}`. The slot is narration-free, so every later section start shifts by that amount.
- **Scene plan:** one fixed scene `channel_intro` (type `animation`, `narrative_role: transition`) at the slot, using the brand clip. Nothing to generate.
- **Assets:** copy `brand.intro.<format>.file` and `audio` into the project's `public/` folder and list them in the asset manifest as "channel brand asset", cost 0.
- **Edit / compose:** play the clip muted inside the composition and schedule its sting in the mix, in the narration-free gap, at the level in `brand.intro.sting_level` (peaks at or below -6 dBFS). This is the one sanctioned exception to atelier's "no reuse of finished components": a finished brand asset is reused, scene components never are.
- **Shorts:** `brand.intro.shorts.mode: end_bug` means no intro; show the circle-masked logo as a small bug with the short sting for the last `seconds` of the Short.
- **Publish:** write the pinned starter comment and the description's source list from `publishing.pinned_comment` and `publishing.sources`, and remind the user to turn on comment hold-for-review.

The profile's standing opening structure (`formats.long_form.structure` and `script-guide.md`) works the same way: it is the default the proposal starts from. A one-off deviation is logged as a `playbook_override`; only the user making it a standing preference changes the channel's files.

### 5. Voice Audition (when `narration.voice_audition_required: true`)

On the channel's first video, before the full narration run:

1. Ask the user for 2-3 candidate voice IDs. The ElevenLabs key can't list voices, so the user supplies IDs from the voice library or uses voice design.
2. Render the same riskiest sample section with each candidate and play them back.
3. After the user picks one, write the winner into `channel.yaml`: set `voice_id`, set `voice_audition_required: false`, and replace the draft `planning_wpm` with a measured value. For a character voice, write it into `characters.md`.
4. Remove the answered item from `open_questions`.

## Rules

- **A profile supplies defaults, never permission.** Approval gates, the "Present Both Composition Runtimes" rule, the composition-mode choice, announcing paid calls, and AI-video approval all still apply. "The channel profile says remotion" is a recommendation to present, not a decision already taken.
- **One-off deviations are logged, not written back.** If the user wants something different for one video, log it in `decision_log` (e.g. `playbook_override`, or a `voice_selection` with the channel default in `options_considered`). Leave the profile unchanged.
- **Standing preferences go into the channel's files.** When the user says "always do X for this channel", edit that channel's `channel.yaml`, `script-guide.md` or `characters.md`. Don't write it to global memory or to `storytelling.md`. Validate with `load_channel` afterwards.
- **A preference for every channel stays global.** It belongs in the shared skills or global memory, not copied into five profiles.
- **Write channel files as UTF-8.** Use the Edit/Write tools or Python with `encoding="utf-8"`. Never use PowerShell `Set-Content`/`Out-File`: it corrupts Devanagari or adds a BOM.

## Add a Channel

1. Copy `channels/_template/` to `channels/<new-id>/`. The id is kebab-case and matches the folder name.
2. Interview the user, or draft for them to review: language, formats (long-form, Shorts, or both), what the channel makes, pipeline, look (pick an existing playbook, or create one in `styles/` and validate it with `validate_playbook` and `validate_accessibility`), voice, register, structure, humor, visuals, music, policies.
3. Write `script-guide.md` with example lines in the channel's language and a structure section per format. If there is a recurring cast, copy `_template/cast/` and set `visuals.cast_dir: cast` for a structured bible (preferred for story channels), or add a prose `characters.md`.
4. Validate it with `load_channel('<new-id>')`, run `tests/contracts/test_channel_profiles.py`, and add a row to `channels/README.md`.
