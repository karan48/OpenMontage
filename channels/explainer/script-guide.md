# Script Guide: Curious India (Hindi explainers — long-form and Shorts)

Read this after `skills/creative/storytelling.md`. Where they conflict on register, structure or humor level, this guide wins. Plain language comes first on this channel too: give an everyday Indian analogy before any jargon.

Quality bar: `projects/himalaya-glacier-timebomb-hindi`.

## Voice and register

The narrator is a warm, direct friend who talks to you in second person with "आप". They are not a documentary host describing events from a distance.

- Put direct-address connectors at section openings and transitions:
  - "अब आप पूछेंगे…" instead of "अब सवाल ये है…"
  - "मैं आपको दिखाता हूँ…" instead of "यहाँ बताया जाता है…"
  - "चलिए, साथ में…" for callbacks
- A handful of these per script is enough. This is not a rewrite into casual chatter.
- Always "आप". Never "तू" or "यार".
- **Grave beats stay restrained.** Any section about real human cost or tragedy keeps a grave delivery. Direct address can still appear there ("मेरे साथ रहिए") as a friend asking you to stay through something hard. It never becomes a warmth upgrade that undercuts the gravity.

## Long-form structure (10-15 min): teaser, then the video

1. **Cold open**, read like a case file: the strangest concrete fact, in the first 5-15 s.
2. **Three numbered open loops**, none resolved in the teaser. A `1 / 3` promise-counter chip tracks them on screen.
3. **The promise.** The narrator's first "मैं" line plants a thesis sentence. Echo that sentence verbatim near the end.
4. **Title card.**
5. **The video.** Each section escalates on the last, with a curiosity beat every 20-40 s. Each open loop is paid off visibly (`1 / 3 ✓`).
6. **Landing.** The thesis echo, a callback to the opening image, and something the viewer can share.

Skip origin stories and background the audience already knows. A 1-2 line recap in the teaser is enough.

## Shorts structure (45-60 s)

Same narrator, same "आप" register, compressed. There is no teaser and no title card.

| Time | Beat |
|---|---|
| 0-2 s | **The strangest fact**, stated flat. No "नमस्ते", no topic intro. |
| 2-40 s | **One idea, told as a mini-mystery.** One question, 2-3 escalating facts, one everyday analogy. |
| 40-55 s | **The reveal.** |
| last 3-5 s | **Pointer to the full video**, if there is one ("पूरी कहानी — full video में"). Otherwise a one-line takeaway. |

**Cut-downs** from a long video take its single strongest beat, usually a teaser open loop or the biggest reveal. Re-voice the opening line so it works cold. Don't start mid-sentence from the long video. Reuse the long video's scenes, reframed to 9:16, with text kept out of the Shorts UI zones (bottom 20%, right 15%).

**Standalone Shorts** follow the same beat map with fresh visuals.

## Length and timing

- Plan at **~156 wpm** (measured on `eleven_v3` with this voice). 10-15 min of speech is about **1,550-2,350 Hindi words**, plus silences. A 45-60 s Short is about **115-155 words**.
- Never time a new script off another artifact's `total_duration_seconds`. Those are plans the renders never matched.
- Write in section-sized chunks aligned to narrative beats. Each chunk carries its `delivery_cues.provider_text` with eleven_v3 audio tags: `[curious]`, `[sighs]`, `[whispers]`, `[mischievously]`, `[sarcastic]`, `[serious]`, `[pause]`, and others.
- Before any TTS spend, deliver a tagged-script HTML/MD for review. Then render 1-2 sample sections at the riskiest tonal pivot and get a listen-and-approve.
- After a direct-address or tag pass, re-run the `skills/meta/script-reviewer.md` consistency check: `text` vs `provider_text`, and `emphasis_words` present verbatim.

## Hooks

Work well here:
- A concrete, strange fact: "कल्पना कीजिए…" followed by a number that shouldn't be true.
- A case-file cold open.
- A myth stated confidently, then cracked.

Avoid "नमस्कार दोस्तों", "welcome back", or any preamble before the mystery.

## Humor

Medium. Look for irony, bureaucratic absurdity and relatable comparisons, especially in dry, statistical sections. The comic energy belongs to the absurdity beats. Pivot hard to grave and respectful the moment real human cost enters the story.

## Never

- Jargon before its analogy.
- Mocking victims or communities.
- An AI face of a real named person.
- Exact text (numbers, dates, names) baked into a generated image.
