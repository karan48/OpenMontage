# OpenMontage - Agent Guide

Start here. This is the core operating contract for OpenMontage. It is short on purpose: detailed procedures live in `docs/agent/` and are read **only at the stage that needs them** (see "Where the Details Live"). Everything in those files is as binding as this page.

For architecture, key files, and conventions see [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md).

## Where the Details Live

| File | Contents | Read when |
|---|---|---|
| `docs/agent/governance.md` | Full Decision Communication Contract, reference-video workflow, channel-profile steps, project layout, stage contracts, communication protocol | proposal; any provider/model/runtime change; any blocker |
| `docs/agent/preflight.md` | Preflight, provider menu, setup offers, capability discovery, tool families and naming, planning protocol, music plan | idea / proposal |
| `docs/agent/composition-runtimes.md` | Runtime HARD RULE in full, templated vs atelier, `video_compose` engines, motion-required rule, Remotion scene types | proposal, edit, compose |
| `docs/agent/layer-map.md` | Architecture overview, Layer 3 skill table, style playbooks, Ink Theater, quick lookup | before the first generation-tool call or playbook choice |

Read each file once, at the stage that needs it. Do not preload them all.

## Context Budget

Token usage is dominated by context size: every call re-sends the whole session, so a session at 800k context costs ~16x one at 50k per turn. Keep it small.

- **One stage per session.** Checkpoints live on disk, so a fresh session resumes cleanly with `/next-stage <project-id>`. At every human gate, end with: "Good point to `/clear`, then `/next-stage <project-id>`." If you stay in one session, `/compact` at the gate.
- **Read only this stage's files:** the current director skill, the channel files, the previous stage's artifact, and the `docs/agent/` file for this stage. Never re-read earlier stages' director skills.
- **Large files:** never Read a file over ~40 KB whole. Grep first, then Read with `offset`/`limit`. Do not re-read a file after editing it; Edit fails loudly if the change did not apply.
- **Compositions:** split hand-authored compositions into `act*.tsx` files. Never grow one `Composition.tsx` past ~30 KB.
- **Images:** downscale frames to ≤768 px wide before reading, review them as contact sheets, and re-read only the frames that changed.
- **Command output:** send renders, installs and long scripts to a log file and read the tail (`> log 2>&1; tail -20 log`). Scripts print summaries, never full JSON dumps.
- **Web research:** distill it into the `research_brief` and move on. Do not keep re-fetching pages.

## First Interaction — Onboarding

When the user's first message is vague or exploratory ("make me a video", "what can you do?"), read `skills/meta/onboarding.md` **before** doing anything else. When the user arrives with a specific, actionable request, skip onboarding and go directly to Rule Zero.

## Reference Video Entry Point

When the user gives a **video URL or local video file as inspiration** ("make me something like this"), read `skills/meta/video-reference-analyst.md` and run its analysis workflow (`video_analyzer`, transcript, scene detection, frame sampling). Summarize the reference's content, pacing, structure, style and what makes it work, then run the capability audit and pipeline selection, and present 2-3 differentiated concepts, not a carbon copy. Never fall back to plain search + guesswork.

"Edit this footage" / "cut this into clips" is a source-footage request instead: use `source_media_review` and a footage-led pipeline. Full text: `docs/agent/governance.md`.

## Channel Profiles — Which Channel Is This For?

The user runs several YouTube channels. Each has its own language, format, narration voice, script style, look and policies in `channels/<id>/` (`channel.yaml`, `script-guide.md`, optional `characters.md`). **Every production request belongs to a channel.**

Before Rule Zero's step 1, **read `skills/meta/channel-profiles.md`**. Then:

1. Identify the channel (`lib.channel_profile.list_channels()`). If the user didn't name one, **ask**. Never guess silently.
2. Identify the format: **long-form** (16:9) or **Shorts** (9:16). Every channel makes both, so ask if it's unclear.
3. Load the profile with `load_channel('<id>')` and the format with `resolve_format(profile, '<long_form|shorts>')`. Pass `channel=` and `video_format=` to `init_project`.
4. Use the profile's pipeline, playbook, voice, the format's structure, length, composition mode and pacing, the script guide and the character bible as the **defaults** you recommend at each stage.

A profile supplies defaults, never permission. Every gate and rule still applies, including "Present Both Composition Runtimes". A standing preference for one channel goes into that channel's files, not into global defaults.

- **Brand intro.** If the profile has a `brand` block, every production in those formats includes it: reserve it at script, place it in the scene plan, copy it at assets, mix it at compose, write the pinned comment at publish. See "Brand intro and standing structure" in `skills/meta/channel-profiles.md`.
- **Recurring characters.** When a story has named or speaking characters (always on a channel with `visuals.cast_dir`), read **`skills/meta/character-bible.md`**. `lib/character_bible.py` builds every character prompt and reference list, and `fal_reference_image` draws the shot. Never hand-type a character's appearance into a prompt.

## Rule Zero — All Production Goes Through a Pipeline

**Every video production request MUST go through the pipeline system. No exceptions.**

When the user asks to make, create, produce, or generate any video content — a trailer, explainer, clip, animation, or any other video — the agent must:

1. **Identify the pipeline.** Match the request to one of the pipelines in `pipeline_defs/`. If unclear, ask the user.
2. **Read the pipeline manifest.** `pipeline_defs/<pipeline>.yaml` — know the stages, tools, and quality gates.
3. **Run preflight.** Discover available tools via the registry. Present the capability menu.
4. **Execute stage by stage.** For EACH stage, read the stage director skill (`skills/pipelines/<pipeline>/<stage>-director.md`) BEFORE doing any work in that stage.
5. **Read Layer 3 skills before calling tools.** Before using any tool with an `agent_skills` field, read the referenced skill in `.agents/skills/`. These contain provider-specific prompting guidance, parameter optimization, and quality techniques that dramatically improve output.

**Do NOT:**
- Write ad-hoc Python scripts to call tools directly
- Skip the pipeline and go straight to API calls
- Generate assets without reading the stage director skill first
- Use a tool without checking its Layer 3 skill for prompting guidance
- Bypass preflight, checkpoints, or review

The intelligence is in the skills, not in improvised code. An agent that reads the director skills and Layer 3 knowledge will produce significantly better output than one that calls tools directly with generic prompts.

## Decision Communication Contract

For any meaningful production decision, communicate the decision before acting. The user should never have to infer which provider, model, or render path was chosen. Condensed here; full text in `docs/agent/governance.md`.

### Announce Before Execution

Before any paid or consequential generation call, state the exact tool name, the provider, the model or provider variant, why it was chosen, and whether it is a sample or a batch run.

### Ask Before Major Changes

Ask before switching provider, switching model family or variant, switching from video-led to still-led treatment, switching composition engine when that changes the output's character, dropping narration, music or other approved elements, or changing from sample mode to batch mode. Minor prompt refinements inside an approved provider/model path don't need separate approval unless they materially change the creative direction.

### Re-log Changed Decisions (Binding)

`decision_log` is append-only history. When a logged choice changes, **append** a new entry with the **same `category` AND the same `subject`**, move the superseded option into `options_considered`, and set `rejected_because` to note the change. Never mutate the old entry or reword the subject. Editing only a downstream artifact while the old decision stays in the log is a defect. Applies at every stage.

### Present Both Composition Runtimes (HARD RULE)

When both Remotion and HyperFrames are available (check `video_compose.get_info()["render_engines"]`), the agent **MUST present both options to the user** before locking `render_runtime` at the proposal stage. For each one, give what it is best at for this brief, an honest tradeoff, and your recommendation tied to the brief. Silently picking a "default" is forbidden, even when the pipeline manifest or a director skill suggests one. Wait for explicit approval, and record both runtimes (plus any ffmpeg option) as `options_considered` in the `render_runtime_selection` decision. If only one runtime is installed, say so explicitly and record the other with `rejected_because: "runtime not available on this machine"`. This applies to every pipeline that invokes `video_compose`. Full text: `docs/agent/composition-runtimes.md`.

### Composition Authoring Mode

**Templated** assembles the stock `cut.type` scene types: fast, cheap, and the reason most videos look alike. **Atelier** hand-authors the composition from scratch (`composition_mode: "atelier"`). Present it as its own proposal decision (`decision_log` category `composition_mode`). Default to atelier for hero work. In atelier the stock scene catalog, `hyperframes-registry` blocks, fixtures and finished components are off-limits. Route through `skills/meta/taste-direction.md`, then `skills/meta/bespoke-composition.md`, and close with a distinctness review. Atelier costs more tokens; say so at proposal. Full text: `docs/agent/composition-runtimes.md`.

### Escalate Blockers Explicitly

Surface a blocker immediately with: (1) what was attempted, (2) what failed, (3) whether it is auth, provider access, a tool bug, or prompt/design quality, (4) what options exist, (5) which option you recommend and why. Do not continue with a substitute path until the user approves.

### Recommendation Style and No Unilateral Substitutions

When asking the user to choose, give the shortlist, brief tradeoffs and one recommendation, then wait for approval. If the approved path is blocked you may prepare alternatives, but never execute them without approval. This applies especially to provider swaps, model swaps, fallback tools, prompt-only substitutes for reference-driven generation, and still-image animatics in place of true motion.

## Orchestrator

The agent itself orchestrates the production state machine:

`research -> proposal -> script -> scene_plan -> assets -> edit -> compose`

The agent:

1. Reads the pipeline manifest (`pipeline_defs/*.yaml`) to know the process
2. Calls `checkpoint.get_next_stage()` to find where to resume
3. Reads the stage's director skill (`skills/pipelines/<pipeline>/<stage>-director.md`) to know HOW
4. Uses tools (`tools/`) for concrete capabilities
5. Self-reviews using the reviewer meta skill (`skills/meta/reviewer.md`)
6. Checkpoints via the checkpoint protocol (`skills/meta/checkpoint-protocol.md`)
7. Presents to human for approval when `human_approval_default: true`

Infrastructure files:

- `lib/checkpoint.py` — read/write checkpoints, stage validation
- `tools/cost_tracker.py` — budget governance
- `lib/pipeline_loader.py` — manifest loading and helpers

## Project Directory Convention

Every production run lives in `projects/<project-id>/` (gitignored; kebab-case from the title): `artifacts/` for stage JSON, `assets/{images,video,audio,music}/`, and `renders/final.mp4`.

At pipeline initialization, before any stage runs:

1. **Initialize the workspace**: `python -c "from lib.checkpoint import init_project; init_project('<project-id>', title='<Title>', pipeline_type='<pipeline>', channel='<channel-id>', video_format='<long_form|shorts>')"`. Omit `channel` and `video_format` only for a production that belongs to no channel.
2. **Open the board**: `python -m backlot open <project-id>`. If it fails, continue; the board is an observer, never a blocker.

**Always pass an explicit `output_path` under `projects/<project-id>/`.** This applies to atelier and HyperFrames runs too. Full text: `docs/agent/governance.md`.

## Available Pipelines

Production: `animated-explainer`, `screen-demo`, `cinematic`, `animation`, `hybrid`, `avatar-spokesperson`. Beta (mention rough edges when selected): `talking-head`, `clip-factory`, `podcast-repurpose`, `character-animation`, `localization-dub`. Test: `framework-smoke`. Descriptions: `docs/agent/preflight.md`.

## Mandatory Preflight

Before any creative work, run the human-ready rollup. Never paste the raw `support_envelope()` firehose.

```bash
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_menu_summary(), indent=2))"
```

Present it as a capability menu ("X of Y configured" per capability; what works now and what could be unlocked). Surface `runtime_warnings` verbatim. Check the manifest's `required_tools` and `fallback_tools`, then report `passed`, `degraded`, or `blocked`. Never hardcode provider names, key names, or setup URLs; read `install_instructions` from the registry. Full procedure and menu format: `docs/agent/preflight.md`.

### Setup Offer Protocol

When a tool is unavailable but fixable (env var, install), offer setup help. Say what it would unlock and the cost difference, and group tools that share an env var. If the user declines, proceed with the best available path. No nagging. Details: `docs/agent/preflight.md`.

### Composition and Motion

`video_compose` routes to FFmpeg, Remotion or HyperFrames by `edit_decisions.render_runtime`, which is locked at proposal and carried through unchanged. For motion-required briefs (trailers, hype edits, avatar videos), still-image or FFmpeg-only fallback is forbidden, and a silent runtime swap is forbidden; surface a blocker instead. Details: `docs/agent/composition-runtimes.md`.

### Tools

Query the registry (`capability_catalog()`, `provider_catalog()`); never rely on memory or hardcoded tool lists. Tool classes are PascalCase without a `Tool` suffix (`ElevenLabsTTS`, `VideoCompose`). Call them with `.execute(params_dict)`, which returns a `ToolResult` (`.success`, `.data`, `.error`); never `.run()`. Multi-provider capabilities route through `tts_selector`, `image_selector` and `video_selector`. Details: `docs/agent/preflight.md`.

## User-Facing Planning Protocol

Before committing to execution, present:

1. Concept directions (4-5 when the brief is still open).
2. The recommended pipeline.
3. The recommended tool path and the alternative paths that are actually available.
4. Cost estimate and quality tradeoffs.
5. The **music plan**. It is mandatory whenever there is audio: tracks in `music_library/`, music APIs, a user-provided track, or no music. Surface it at proposal, never as a surprise at the asset stage.
6. The production plan by stage.
7. An approval gate before asset generation.

Details: `docs/agent/preflight.md`.

## Stage Agents

Each stage produces one canonical artifact (`brief`, `script`, `scene_plan`, `asset_manifest`, `edit_decisions`, `render_report`) that becomes the contract for the next stage. The stage director skill (`skills/pipelines/<pipeline>/<stage>-director.md`) teaches how to produce it.

- A completed or awaiting-human checkpoint must include the stage's canonical artifact.
- Canonical artifacts must validate against the JSON schema in `schemas/artifacts/`.
- Media files belong in stage-specific directories. Tools record seeds and model versions.

Quality bar per stage: `docs/agent/governance.md`.

## Reviewer Protocol

The reviewer is a meta skill (`skills/meta/reviewer.md`) — advisory, never directly blocks progression.

- Self-review after every stage execution, before checkpointing.
- Load `review_focus` items from the pipeline manifest for the current stage.
- Maximum two review rounds. After that, pass with warnings and move on.
- Findings categorized: critical (must fix), suggestion (should fix), nitpick (nice-to-have).
- Critical findings -> fix and re-review. Suggestions -> note and proceed.
- Check playbook `quality_rules` as constraints, not suggestions.

## Human Checkpoint Protocol

The checkpoint protocol meta skill (`skills/meta/checkpoint-protocol.md`) teaches the agent when to pause:

- Read `human_approval_default` from the pipeline manifest per stage. **The manifest value is binding** — never re-judge it. `lib/checkpoint.py` enforces this: a gated stage cannot be written `completed` without `human_approved=True`.
- Typical gated stages: `idea`/`proposal`, `script`, `scene_plan`, **`assets`** (review the generated assets scene-by-scene — the Backlot board's filmstrip — before compose locks them in), and `publish` where the pipeline has one. Most pipelines auto-proceed on `edit` and `compose`, but not all (documentary-montage gates `edit`) — the manifest you loaded is the only authority.
- When approval is required: write the checkpoint as `awaiting_human`, present artifact summary, review findings, and cost snapshot — then **END YOUR TURN**. Doing further pipeline work in the same response is a gate violation.
- **Approval is per-gate.** An early "go ahead" never covers later gates; explicit full-run pre-authorization must be recorded as a `decision_log` entry (`category: "approval_policy"`) to count.
- Wait for human to approve, request revision, or abort.

## Communication Protocol

Agents coordinate through canonical JSON artifacts, checkpoints, pipeline manifests, and the tool registry. Key paths: artifact schemas in `schemas/artifacts/`, the checkpoint schema in `schemas/checkpoints/checkpoint.schema.json`, manifests in `pipeline_defs/`, playbooks in `styles/*.yaml`, the tool contract in `tools/base_tool.py`, the registry in `tools/tool_registry.py`, and meta skills in `skills/meta/*.md`.

- Checkpoints live at `projects/<project_id>/checkpoint_<stage>.json`. `status` is `completed`, `failed`, `awaiting_human`, or `in_progress`.
- Write an `in_progress` checkpoint on entering each stage. During `assets`/`compose`, refresh `metadata.partial_progress` after each unit; this powers the board.
- A gated stage can only be written `completed` with `human_approved=True`.
- Superseded checkpoints are archived to `projects/<project_id>/history/`. Invalid checkpoints or artifacts fail fast.
- Every production tool inherits from `BaseTool`, and discovery goes through the registry.

Full text: `docs/agent/governance.md`.

## Style Playbooks and Skill Layers

Playbooks live in `styles/*.yaml`, and each channel profile names its default. For custom, atelier, brand, launch, or hero work, read `skills/meta/taste-direction.md` before choosing a playbook and carry its `taste_profile` into the proposal. For hand-drawn doodle looks, use Ink Theater (`skills/creative/ink-theater.md`).

OpenMontage has three instruction layers: `tools/` (what exists: the registry), `skills/` (how OpenMontage uses it: Layer 2), and `.agents/skills/` (vendor knowledge: Layer 3). **Layer 3 is not optional:** before calling any generation tool, read the skills in its `agent_skills` field. Prefer skills over tool source code, except when debugging or auditing. The playbook table, the Layer 3 category table and the quick lookup are in `docs/agent/layer-map.md`.

## What Not To Do

- **Do not bypass the pipeline.** Never write ad-hoc scripts to call tools directly. All production goes through pipeline stages with director skills. See Rule Zero.
- **Do not call generation tools without reading their Layer 3 skill.** Check the tool's `agent_skills` field, read the referenced skill, then craft your prompts using that guidance.
- **Do not skip stage director skills.** Before executing any pipeline stage, read its director skill. The skill contains the quality bar, the workflow, and the review criteria.
- Do not use deleted legacy names such as `tts_cloud`, `tts_engine`, or `video_gen`.
- Do not hardcode provider names, API key names, or setup URLs. Read them from the registry's `install_instructions` and `dependencies` fields.
- Do not begin asset generation before user approval on the production plan.
- Do not hide degraded paths. Record substitutions and blocked options explicitly.
- Do not present a single unavailable tool in isolation. Always show the full capability picture: "X of Y providers configured for this capability."
- Do not skip the Provider Menu at preflight. The user must see what they have AND what they could unlock.
- Do not change provider, model, or render path without telling the user first and getting approval when the change is material.
- Do not preload every `docs/agent/` file or re-read files already in context. See "Context Budget".
