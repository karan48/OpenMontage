# Storytelling & Narrative Structure for Explainer Videos

> Sources: YouTube Creator Academy, Derek Muller PhD thesis (U. Sydney 2008), Kurzgesagt production
> methodology (Philipp Dettmer), 3Blue1Brown (Grant Sanderson), Richard Mayer "Multimedia Learning"
> (Cambridge UP, 2001/2020)

## Universal Script-Writing Checklist (Apply Before Every Script)

This checklist applies to every pipeline that writes narration or on-screen copy, not only the
explainer arc below. Run it before drafting and again at self-review (Step 6 / Quality Gate in the
relevant script-director skill).

1. **Know the audience.** Before writing, answer: who is this for, what problem or curiosity do
   they have, why would they click, why would they stay. Write for one person, not everyone.
2. **One main promise.** Every script answers ONE clear question. Five questions in one video means
   viewers lose the thread. State the promise in a single sentence before writing prose.
3. **Strong hook (first 5-15s).** Surprise, curiosity, mystery, a challenged belief, or stakes.
   Never "Hello everyone, welcome back..." See Hook Types below for concrete patterns.
4. **Make the promise explicit.** Tell the viewer why staying to the end is worth it ("By the end
   of this video, you'll understand why experts still disagree").
5. **Follow a story structure.** Hook -> Context -> Rising mystery/conflict -> Evidence and
   discoveries -> Twist -> Resolution -> Final takeaway. Even procedural or data-led scripts benefit
   from this shape; see the Explainer Arc Template below for the timed version.
6. **Build curiosity every 20-40 seconds.** Reintroduce a question with connective phrases ("But
   that's only part of the story...", "Then something changed.", "However, new evidence tells a
   different story."). Pairs with the Pattern Interrupt row in Pacing Rules below.
7. **Change visuals frequently.** Alternate AI-generated images, maps, animations, timelines,
   documents, close-ups, wide shots, and text highlights. Static scenes lose viewers.
8. **Write like you speak.** Conversational language beats academic phrasing — "When archaeologists
   started digging, they found something unexpected," not "Archaeological excavations indicate..."
9. **One idea per sentence.** Break compound sentences into short, sequential statements. Spoken
   narration cannot carry stacked clauses.
10. **Show, don't just tell.** Describe the concrete, visualizable moment, not the abstract summary
    — "Imagine thousands of handwritten manuscripts disappearing into flames," not "The library
    burned." This is the same discipline as the Anti-Subjective Rule below: describe the visual
    cause, not the feeling.
11. **Add emotion.** Wonder, suspense, shock, inspiration, empathy, triumph. Viewers remember
    emotions more than facts.
12. **Build toward a reveal.** Plant clues, let the viewer form a hypothesis, then reveal. Don't
    front-load the answer. See Guided Discovery below.
13. **Reward the viewer.** Deliver on the opening promise with a real answer grounded in the
    evidence presented — don't leave the question dangling.
14. **End strong.** Close with a thought-provoking question, a key insight, a connection to the
    present, or a memorable takeaway. Never just "Thanks for watching."
15. **Keep the pace moving.** Every sentence should introduce an idea, raise a question, answer a
    question, raise the stakes, or reveal new information. If a sentence does none of these, cut it.
16. **Verify facts.** Especially for history, science, medicine, and current events: check reliable
    sources, separate evidence from interpretation, and distinguish established fact from
    traditional account and speculation. Every claim should be traceable to the `research_brief` —
    see each pipeline's "Mid-Production Fact Verification" step.
17. **Design for audio.** Read the script aloud. If a sentence is hard to say, it's hard to hear.
18. **Design for visuals.** For every paragraph, ask "what will viewers be looking at during this
    sentence?" and let the answer drive the enhancement cue.
19. **Make every section better than the last.** Escalate: interesting -> more interesting ->
    surprising -> biggest reveal -> strong conclusion. Treat it as climbing a staircase, not a
    plateau.
20. **Finish with value.** The viewer should leave with a new fact, a new perspective, a memorable
    story, or a reason to share the video.
21. **Default to the common viewer, not the expert.** See "Plain-Language & Humor Default" below —
    this is mandatory unless the brief names a specialist audience.

## Plain-Language & Humor Default (Mandatory)

Unless `proposal_packet.selected_concept.target_audience` explicitly names a specialist/technical
audience (engineers, developers, policy professionals, medical practitioners), **every script
defaults to the general, non-expert viewer** — a smart person with no background in the topic.
This is a standing project preference, not a per-video judgment call: apply it automatically.

**Channel profiles tune the dial.** When the project belongs to a channel (`project.json` →
`channel`), that channel's `channels/<id>/script-guide.md` and `script.humor` level
(none/low/medium/high) set the register, how much humor to use, and the language of the
examples. A cinematic documentary Short runs low, a cartoon story runs high. Plain-language-first
and the humor hard limit below apply to every channel.

- **Analogy before jargon.** Never introduce a technical term cold. Explain the idea through a
  concrete, everyday analogy first — something from ordinary life, not another abstract concept —
  then attach the technical term afterward as a label, not a starting point.
- **Culturally local analogies for the target audience.** For an Indian-audience script, reach for
  daily-life Indian reference points (the postman and a sealed chitthi, exam/school life, sarkari
  daftar paperwork, a kirana shop, a train journey) before reaching for Western media references —
  they land faster and feel like the narrator actually knows the viewer.
- **Humor is a retention tool, not decoration.** Actively look for places to be funny — irony,
  bureaucratic absurdity, a wry aside, a relatable comparison ("like passing an exam without
  reading the textbook"). Humor keeps technical or dry material (budgets, protocols, statistics)
  from turning into a lecture. It is not optional garnish; treat "where can this be funny" as a
  required question for every section, the same way enhancement cues are required.
  - **Hard limit:** never mock victims, communities, tragedy, or genuine human cost. Humor targets
    systems, absurdity, and irony — not people who suffered. See the Anti-Subjective Rule and use
    the same judgment the india-independence-1947-hindi reference project uses: comic energy
    through the bureaucratic-absurdity beats, hard pivot to grave/respectful the moment real human
    cost enters the story.
- **Write like storytelling, not a definition dump.** Address the viewer directly ("सोचिए...",
  "अब सवाल ये है..." / "picture this...", "here's the question"). Build every explanation as a
  small reveal the viewer discovers, not a fact being read to them. Use the Guided Discovery method
  above even for short technical asides.
- **Self-check before submitting:** could a viewer with zero background explain the core idea back
  to a friend afterward, using the analogy you gave them — and would they smile at least once while
  doing it? If either answer is no, revise.

## The Explainer Arc Template

For a **3-minute explainer video** (scale proportionally for other lengths):

```
[0:00 - 0:08]  HOOK
               Pattern interrupt or counterintuitive claim. 1-2 sentences max.
               Visual: striking image or animation that creates curiosity.

[0:08 - 0:30]  TENSION / INFORMATION GAP
               "Here's what most people think... but that's not quite right."
               Establish stakes: why should I care?
               Visual: show the misconception or the puzzle.

[0:30 - 0:50]  CONCEPT 1 (Foundation)
               Simplest building block needed. ONE idea, ONE visual.
               End with a "but" or "therefore" transition.

[0:50 - 1:15]  CONCEPT 2 (Complication)
               Build on Concept 1. Introduce the wrinkle.
               Visual: transform/evolve the previous visual.

[1:15 - 1:20]  PALETTE CLEANSER
               Brief pause, visual gag, or "let that sink in" moment.
               Gives working memory a beat to consolidate.

[1:20 - 1:50]  CONCEPT 3 (Key Insight)
               The "aha" moment. Core of the video.
               1-3 seconds of deliberate silence after the reveal.
               Visual: the most polished animation in the video.

[1:50 - 2:20]  PROOF / EXAMPLE
               Concrete demonstration: "Watch what happens when..."
               Visual: show the insight working in a specific case.

[2:20 - 2:45]  IMPLICATIONS / "SO WHAT?"
               Connect back to the real world. "This means that..."
               Scale from specific back to general.

[2:45 - 3:00]  REFRAME + CLOSE
               Callback to the hook. Restate the core insight in one sentence.
               Optional: open a new curiosity gap.
```

## Scaling by Duration

| Length | Concepts | Hook | Tension | Core | Proof | Close |
|--------|----------|------|---------|------|-------|-------|
| 1 min | 1-2 | 5s | 10s | 30s | 10s | 5s |
| 2 min | 2-3 | 8s | 15s | 60s | 25s | 12s |
| 3 min | 3-5 | 8s | 22s | 100s | 30s | 15s |
| 5 min | 5-8 | 10s | 30s | 180s | 50s | 20s |

## Anti-Subjective Rule

> Hooks, beats, and section descriptions in OpenMontage scripts must describe the **visual cause** of the emotion, not the emotion itself. The CMU/Harvard CHAI study showed that subjective phrasing varies wildly across annotators and across model interpretations — so it does not constrain pixels and it doesn't reliably guide downstream generation tools.
>
> | Avoid | Use instead |
> |---|---|
> | "epic reveal" | "wide aerial pull-back; subject silhouetted against rising sun" |
> | "inspiring moment" | "low angle on the subject's face; light catches the edge of a tear" |
> | "moody atmosphere" | "low-key key light, lifted shadows by 2 stops, fog volumetrics" |
> | "powerful music swell" | "music drops out at 0:42, holds 1.5s of silence, returns with low taiko at half tempo" |
>
> The rule applies to script narration AND to the metadata fields scene-director consumes. For the universal vocabulary that names these visual primitives, see `skills/creative/video-gen-prompting.md`.

## Subject Transitions in the Script

When a script beat introduces a new subject, kills one off, or hands focus from one subject to another, **name the transition explicitly** so the scene-director doesn't have to infer it. The CMU/Harvard taxonomy uses four labels:

| Label | What it means |
|---|---|
| **revealing** | A new subject enters frame or is uncovered (door opens, camera pans to find them, fog clears). |
| **disappearing** | An existing subject leaves frame or is removed (walks out, fades, eclipsed). |
| **switching** | Focus jumps from subject A to subject B (cut, rack focus, camera whip). |
| **complex-alternating** | Multiple subjects trade focus repeatedly within a beat (debate cross-cutting, ensemble action). |

Add 1-2 sentences in the beat describing the mechanism (cut, pan, reveal-by-light, etc.). This propagates into the scene_plan as a transition primitive.

## Hook Types

| Type | Pattern | Best For |
|------|---------|----------|
| **Contrarian** | "Everything you've been told about X is wrong." | Veritasium-style science/myth-busting |
| **Outcome** | "By the end of this video, you'll understand X." | 3Blue1Brown-style math/concept |
| **Mystery** | "In 1987, something impossible happened..." | Kurzgesagt-style story-driven |
| **Stakes** | "This one mistake costs people X every year." | Practical/how-to content |

## The 30-Second Rule

YouTube data shows **50% of viewer drop-off happens in the first 30 seconds**. The hook + tension
setup MUST be complete by second 30. Retention curves that survive the 30-second cliff typically
retain 40-60% through the full video.

## The "But-Therefore" Method

Never connect sections with "and then." Always use **"but"** or **"therefore."**

**Bad:** "Atoms have electrons, AND THEN those electrons have energy levels, AND THEN..."

**Good:** "Atoms have electrons, BUT they don't behave like tiny planets, THEREFORE we need a
completely new model..."

Applied structure:
```
SETUP:     Here's what you think you know about X.
BUT:       Here's why that's wrong / incomplete / surprising.
THEREFORE: We need to understand Y (the real mechanism).
BUT:       Y creates a new puzzle...
THEREFORE: The actual answer is Z.
THEREFORE: This changes how you should think about X.
```

## Misconception-First Approach (Research-Backed)

Derek Muller's PhD research (University of Sydney, 2008) showed that **videos presenting common
misconceptions FIRST, then refuting them, produce significantly higher learning gains** than videos
that simply present correct information. Viewers who watched "misconception-first" videos scored
higher on post-tests and reported higher engagement.

Apply this: always consider opening with what the audience *thinks* is true before revealing what
*actually* is.

## Guided Discovery (3Blue1Brown Method)

Don't explain the answer. **Reconstruct the reasoning path** so the viewer feels they discovered it.

1. **The Question** — Pose a specific, concrete question
2. **The Naive Attempt** — Show the obvious approach; let it partially work, then break
3. **The Key Insight** — Introduce ONE new idea. Pause visually for 2-3 seconds of silence.
4. **The Build** — Apply the insight step by step. Each step feels inevitable.
5. **The Generalization** — "Notice this pattern works beyond our specific example..."

**Progressive Revelation:** Never show the full picture at once. Build visuals layer by layer.
Each layer arrives exactly when the narration references it.

## Camera Intent Per Beat

When writing a beat, attach one line of camera intent so the scene-director doesn't have to invent it from a blank slate. Use the universal vocabulary in `skills/creative/video-gen-prompting.md` (Subject / Subject Motion / Scene / Spatial Framing / Camera). One line is enough — the scene-director will expand it.

Example beat:

```
[0:30] Concept 1 — atoms aren't tiny planets
Narration: "We grew up imagining electrons as tiny planets orbiting the nucleus..."
Camera intent: medium shot of stylized atom; slow rotation; deep focus.
```

The camera-intent line is consumed verbatim by the scene-director's 5-aspect spec — keep it concrete, no mood adjectives.

## Pacing Rules

| Rule | Value | Source |
|------|-------|--------|
| Narration speed | 150-160 wpm | Kurzgesagt standard (conversational is 170-190) |
| New visual element | Every 3-5 seconds | Kurzgesagt production rules |
| Concept density | Max 1 new concept per 30-45 seconds | Mayer's Segmenting Principle |
| Pattern interrupt | Every 45-90 seconds | YouTube retention data |
| Deliberate silence | 1-3 seconds after key insights | 3Blue1Brown technique |
| Palette cleanser | Every 45-60 seconds | Kurzgesagt production rules |

## Mayer's Multimedia Learning Principles (Applied)

These are the most relevant research-backed rules from cognitive science:

1. **Segmenting** — Max 1 new concept per 30-45 seconds. A 3-min video = 4-6 concept segments.
2. **Signaling** — Use verbal signposts every 30-45 seconds ("Here's where it gets interesting").
3. **Temporal Contiguity** — Narration and visuals must be simultaneous. Learning drops ~30% when offset even by a few seconds.
4. **Coherence** — Remove interesting-but-irrelevant content. "Seductive details" reduce learning by 20-30% on transfer tests.
5. **Modality** — Use narration (audio) + visuals (animation), NOT on-screen text + visuals. Spoken words + pictures outperform written words + pictures.

## Applying to OpenMontage

When writing a **script artifact** for the animated-explainer pipeline:

1. Choose a hook type from the table above based on the topic
2. Structure sections using the Explainer Arc template
3. Apply "but-therefore" connectors between sections
4. Consider the misconception-first approach for science/technical topics
5. Set `narration_wpm: 155` in the script to calculate accurate timing
6. Plan visual changes every 3-5 seconds in the scene_plan
7. Mark "silence" beats in the script for key insights
8. Validate: total concepts should not exceed the scaling table above
