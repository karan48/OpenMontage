# Script Reviewer — Meta Skill

## When to Use

Run this pass on every `script` artifact, in every pipeline, **before** it is checkpointed as `awaiting_human`. It runs in addition to — not instead of — the general stage review in `skills/meta/reviewer.md` (schema validation, `review_focus`, `success_criteria`). That skill checks the artifact is *structurally sound*; this skill checks the script is actually *good to watch and easy to listen to*, which needs a script-specific pass no generic stage checklist catches.

**Binding rule:** if this review turns up any `critical` finding, fix it and re-run the review before checkpointing. Do not present a script to the user with an unresolved critical finding — that defeats the point of reviewing before their time is spent on it. Only genuine creative-direction choices (tone, angle, which analogy to use) belong in front of the user; mechanical/consistency issues should already be fixed by the time they see it.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/script.schema.json` | Structural validation (already covered by `meta/reviewer.md`) |
| Skill | `skills/creative/storytelling.md` | Universal checklist + "Plain-Language & Humor Default" — the bar this review measures against |
| Prior artifact | `proposal_packet.selected_concept` | Hook, key_points, tone, target_audience — what the script promised to deliver |
| Prior artifact | `research_brief` | Source of truth for every factual claim |

## Protocol

### Step 1: Hook Timing Check (first ~15s)

The single highest-leverage check. Read only `sections[0].text` (and `sections[1]` if the hook spans two short beats) and time it against `sections[0].start_seconds`/`end_seconds`.

- Identify the sentence that actually delivers the hook's core claim/surprise/stakes (per `storytelling.md` → Hook Types: contrarian, outcome, mystery, stakes).
- Estimate how many seconds into the section that sentence lands, using the section's own pacing (words so far ÷ total section words × section duration).
- **Critical** if the hook claim doesn't land within the first ~15 seconds, or if the opening 1-2 sentences are pure scene-setting/throat-clearing that could be cut with no loss of information (a generic "कल्पना कीजिए" / "imagine this" opener that delays the actual claim is the most common failure mode — see the `30-Second Rule` in `storytelling.md`).
- **Suggestion** if the hook lands by 15-20s but could plausibly be tightened further.
- Propose a concrete rewrite for any critical finding — don't just flag "hook is slow."

### Step 2: Plain-Language & Word-Choice Check

Cross-check against the "Plain-Language & Humor Default" section of `storytelling.md`.

- For every non-obvious analogy or replaced-jargon term, ask: does this read as something a native speaker would actually say, or does it feel assembled/translated? Flag unnatural noun pairings (e.g. a word normally paired with liquids forced onto light/data) as **suggestion** with a proposed alternative word.
- Confirm technical terms are introduced analogy-first, term-second (not term-first).
- If `proposal_packet.selected_concept.target_audience` names a specialist/technical audience, this check is relaxed — note that explicitly rather than flagging.

### Step 3: Humor & Tone Discipline Check

- Is there at least one genuine light/funny beat per major act (not just the opening)? A script with zero humor when nothing in `target_audience`/`tone` calls for a strictly serious register is a **suggestion**.
- Does any joke land on or near a genuine human-cost/tragedy beat? That is **critical** — humor targets systems and absurdity, never victims (see Anti-Subjective Rule cross-reference in `storytelling.md`).
- Do planted jokes get paid off later (callback), or do they land once and vanish? Missing payoff on an explicitly-planted setup is a **suggestion**.

### Step 4: Internal Consistency Check

Scripts are usually revised in place — this is where stale text survives edits.

- For every section, confirm `text` and `delivery_cues.provider_text` say the same thing (minus audio tags/pauses). A mismatch between the two — one edited, the other left stale — is **critical**; quote both versions in the finding.
- If the script establishes a running analogy or callback phrase (e.g. a recurring comparison, a repeated image), verify every later reference actually reuses it verbatim rather than drifting into a different metaphor. Flag drift as **suggestion**.
- Confirm `delivery_cues.emphasis_words` entries actually appear verbatim in `text` — an emphasis word that doesn't appear is **suggestion** (dead reference).
- Scan for duplicate/leftover fragments from a prior draft (repeated clauses, dangling half-sentences) — **critical**, they read as a generation artifact.

### Step 5: Pacing & TTS-Readiness Check

- For each section, compute words ÷ (duration in minutes) and compare against the script's overall calibrated WPM (see `metadata.word_count_note` or compute from the whole script). A section more than ~30% off the script's own average is **suggestion** — flag it for a re-time pass, since it will visibly rush or drag relative to its neighbors.
- Confirm every `[tag]` in `provider_text` is well-formed (matching brackets, no stray `[` or `]`) — malformed tags are **critical**, they will likely misfire or be read aloud literally by the TTS provider.
- Confirm `pronunciation_guides` cover every foreign/acronym/technical term that appears in `text` for the first time in that section.

### Step 6: Fact Traceability Check

- Every section's `source_ref` should point to a real `research_brief` field or a clearly-labeled callback to an earlier section/`research_summary`. A `source_ref` that doesn't correspond to anything in the research_brief is **suggestion** — "verify or correct this reference."
- Spot-check 2-3 numeric claims against the research_brief's actual data_points — a claim that has drifted from its source (wrong number, wrong year) during rewrites is **critical**.

### Step 7: Decision and Report

Use the same severity/format as `skills/meta/reviewer.md` Step 6-7 (PASS / REVISE / PASS_WITH_WARNINGS, max 2 revision rounds). Fix every `critical` finding before checkpointing `awaiting_human`. Note `suggestion`/`nitpick` findings in the checkpoint's `review` field so they're visible on the Backlot board, but they do not block presenting the script to the user.

## Quick Reference: Common Failure Patterns

| Symptom | Likely cause | Severity |
|---|---|---|
| Hook claim doesn't land until >15-20s in | Opening spends time on scene-setting before the mystery/stakes | Critical |
| A word/phrase feels "off" or forced | Analogy chosen for accuracy over how it actually sounds spoken aloud | Suggestion |
| `text` and `provider_text` say slightly different things | Edit applied to one field, not the other | Critical |
| A joke lands right before/after a human-cost beat | Comic and grave beats not separated by a clear tonal pivot | Critical |
| One section reads noticeably faster/slower than its neighbors | Word count not re-balanced after a rewrite changed section length | Suggestion |
| A planted setup/callback phrase is never reused later | Later section rewritten independently, lost the throughline | Suggestion |

## Integration

- Referenced from `skills/pipelines/explainer/script-director.md` Step 6 (Self-Evaluate) — run this review as part of that step, not as an afterthought.
- Any pipeline with its own script/beat-writing stage (cinematic, animation, documentary-montage, etc.) should reference this skill the same way; it is deliberately pipeline-agnostic.
