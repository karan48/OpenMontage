---
name: documentary-scene-image-prompts
description: Turns a narrated documentary/explainer video script (voiceover text with a stated or implied duration, e.g. "45 second scene") into a numbered list of AI image-generation prompts, one per visual beat, ready to paste into Midjourney, DALL-E, Nano Banana, Stable Diffusion, or any other tool. Handles the timing math for how many images a scene needs, keeps recurring people (narrators, historical figures, hosts) visually consistent across scenes via a persistent character bible, and treats sensitive material (violence, death, trauma) with non-graphic, symbolic imagery. Use whenever the user pastes narration/script text and asks for images, a shot list, or "how many images do I need" -- even without the word "prompt". Also trigger for keeping a character's look consistent across images, changing art style for existing prompts, or building out a multi-scene video project scene by scene.
---

# Documentary Scene → Image Prompts

## What this skill is for

Someone is building a narrated video (YouTube documentary, explainer, history piece, true-crime recap — anything with a voiceover track) and needs one AI image per few seconds of screen time to cut against the narration. They'll hand you a scene's worth of script text and a duration. Your job is to turn that into a shot list: a numbered set of image-generation prompts that (a) covers the runtime at a natural pace, (b) follows the narrative beats of the actual words being said, (c) keeps any recurring person looking like the same person from scene to scene, and (d) is safe and respectful when the material gets heavy.

This is usually not a one-off request — it's scene 1 of N. Treat every invocation as part of a longer-running project: what you decide about a character's face in scene 3 has to still be true in scene 14.

## Step 1: Get the essentials

You need three things. Infer them from context where you reasonably can, ask only when genuinely missing:

- **The scene text.** The actual voiceover/narration for this scene.
- **The duration.** If the user states it ("this is 45 seconds"), use that. If they don't, estimate from word count at roughly 150-160 words per minute of narration and say so, so they can correct you.
- **The visual style.** Default to **photorealistic documentary** (see `references/style-tags.md`) unless the user has asked for something else earlier in the conversation or names a style now (painterly, animated, noir, etc.). If they already established a style for this project, keep using it without re-asking — consistency across scenes matters more than novelty.

## Step 2: Work out how many images the scene needs

Documentary-style videos read comfortably at roughly one new image every 4-6 seconds (images typically get a Ken Burns zoom/pan to stretch further than their raw display time). Don't just divide by 5 and round — run the numbers so the pacing stays inside that comfortable band:

```bash
python scripts/calculate_beats.py --duration <seconds>
```

This prints a beat count and the resulting seconds-per-image. Treat this as a starting point, not a mandate — if the scene has an odd number of distinct narrative ideas (say, 7 natural beats but the math suggests 8), it's fine to match the content rather than force an extra image. The goal is images that each correspond to something actually happening or being said, not a mechanical time-slicing.

## Step 3: Break the scene into beats

Read the narration and find the natural visual turns — new subject, new location, new idea, an emotional shift, a fact being dropped in. Don't split mid-sentence unless the sentence is doing two visually distinct things. Each beat should be a chunk of narration short enough to sit under one image without the image going stale.

For each beat, note: the excerpt of script it corresponds to, and the concrete scene you'd photograph or paint to represent it. Prefer specific, filmable images over abstractions — "a hand hovering a pen over an unmarked map" beats "a decision being made."

## Step 4: Keep characters consistent — the character bible

This is the part that's easy to get wrong across a multi-scene project: if a recurring person gets a different face in every scene, the video looks broken. Maintain a `characters.md` file in the project's working directory as a running bible of every named recurring person.

**Before writing prompts:** check whether `characters.md` exists in the working directory (or ask the user once, up front, where their project files live if it's not obvious). If it exists, read it — any character it already describes must be reused **verbatim**, not paraphrased or re-imagined, in every prompt where they appear. Small rewordings between scenes are exactly how faces drift.

**When a new named recurring person appears** (anyone who's likely to show up again — not incidental background people), write a locked physical description: age, build, hair, distinguishing features, characteristic clothing for the era, general demeanor. Keep it concrete and visual, not biographical. Append it to `characters.md` under that person's name, and create the file with a short header if it doesn't exist yet. This is also the moment to think ahead about how that person should look at different ages if the story will span years — draft an aged variant if you already know it'll be needed, or add one later when it comes up.

A `characters.md` entry looks like:

```markdown
## Cyril Radcliffe
A 47-year-old British man, tall slender build, neatly combed dark hair with a receding hairline, round tortoiseshell glasses, clean-shaven with a thin trimmed mustache, sharp aquiline nose, pale English complexion, wearing a formal 1940s grey three-piece suit with a pocket watch chain, dignified reserved expression.
```

## Step 5: Write the prompts

One prompt per beat, each self-contained (a prompt shouldn't require reading the others to make sense, since they're often generated separately). Structure:

1. The scene/action, written concretely and visually.
2. Any recurring character's locked description, pasted in exactly as it appears in `characters.md`.
3. The style tag for this project (see `references/style-tags.md`), appended at the end of every single prompt so the whole scene — and ideally the whole video — reads as visually unified.

Present the result as a numbered list, each item showing the script excerpt it covers and the full prompt. Include the style tag and any new character-bible entries once at the top rather than repeating the full boilerplate explanation for every item — but the *prompt text itself* should still be copy-paste ready as a complete standalone prompt.

Default aspect ratio is 16:9 for YouTube unless the user is building for Shorts/Reels/TikTok (9:16) or says otherwise — ask if it's genuinely unclear which they're making.

## Step 6: Handle sensitive material with care

Documentary scripts about real historical or current events routinely touch death, violence, displacement, and sexual violence. These are legitimate subjects for serious visual storytelling, but the prompts you write should never ask for graphic, exploitative, or gratuitous depictions — and should never depict sexual violence literally under any circumstances. When narration covers this kind of material, reach for symbolic, respectful imagery instead: empty landscapes, memorial objects, aftermath rather than the act, a portrait's expression rather than a scene of violence. This isn't softening the story — a well-chosen symbolic image often carries more weight than a literal one, and it keeps the output usable. If you're ever unsure whether an image reads as respectful, err toward the more restrained version.

## Step 7: Flag factual issues, don't silently fix them

Documentary scripts sometimes contain small factual errors that would get baked into the wrong visual if you don't catch them (e.g., a script says a banknote showed "another country's Prime Minister" when historically it was a monarch's portrait). If something in the script reads as likely incorrect, say so briefly to the user — one or two sentences, not a lecture — and write the prompt in a way that doesn't lock in the error (use a generic accurate description rather than the specific wrong claim). Let the user decide whether to fix the voiceover; your job is to flag it and not propagate it visually.

## Reference

- `references/style-tags.md` — style tag presets (photorealistic documentary, acrylic painting, and others) plus the standard negative-prompt boilerplate. Read this whenever you need a style tag you haven't already established for the project.
- `scripts/calculate_beats.py` — timing math for step 2.

## A note on generating the images directly

If an image-generation tool is connected and the user asks you to actually run the prompts, you can try — but confirm the model/style fits first, and don't be surprised if it fails on plan/credit limits; that's out of your control. Otherwise, your job ends at delivering copy-paste-ready prompts. Don't apologize at length for not being able to generate — just note it once and move on.

In OpenMontage, actual generation goes through the pipeline and the `image_selector` tool (see `skills/creative/image-gen-usage.md` and `skills/creative/image-provider-usage.md`) — use this skill's output as the shot list / prompt source for that stage rather than calling providers ad hoc.
