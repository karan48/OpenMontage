# Script Guide: Curious India (Hindi explainers — long-form and Shorts)

Read this after `skills/creative/storytelling.md`. Where they conflict on register, structure or humor level, this guide wins. Plain language comes first on this channel too: give an everyday Indian analogy before any jargon.

Quality bar: `projects/himalaya-glacier-timebomb-hindi` (its production quality; its opening structure was replaced on 2026-10-05, see Long-form structure).

**Language.** "Hinglish" on this channel means Devanagari for Hindi plus the English words Indians actually say in English (FIR, takedown, Section 66A, NEET, X, portal) in Latin script. Never Roman-script Hindi.

## Voice and register

The narrator is a warm, direct friend who talks to you in second person with "आप". They are not a documentary host describing events from a distance.

- Put direct-address connectors at section openings and transitions:
  - "अब आप पूछेंगे…" instead of "अब सवाल ये है…"
  - "मैं आपको दिखाता हूँ…" instead of "यहाँ बताया जाता है…"
  - "चलिए, साथ में…" for callbacks
- A handful of these per script is enough. This is not a rewrite into casual chatter.
- Always "आप". Never "तू" or "यार".
- **Grave beats stay restrained.** Any section about real human cost or tragedy keeps a grave delivery. Direct address can still appear there ("मेरे साथ रहिए") as a friend asking you to stay through something hard. It never becomes a warmth upgrade that undercuts the gravity.

## Long-form structure (10-15 min): evidence first, then the story

Standing default since 2026-10-05. The Himalaya teaser took 70 s to reach the story and lost 94.1% to 51.3% of viewers inside 45 s (average view duration 4:21, 0 comments on 360 views). `skills/creative/storytelling.md` says the hook and tension must be complete by 0:30. So the video opens on proof, not on a list of promises.

1. **Evidence-first open (0-45 s).** Two or three dated, checkable evidence contrasts inside the first 30 s: a document against what happened, a rule against its use. The first sentence is a fact (14 words at most), and a real document or data artefact is on screen by 0:05. No "नमस्ते", no definitions, no background, no spoken list of questions. Deliver it at the brisk end of the voice range; grave beats keep their restraint.
2. **The promise.** Two sentences at most, in the narrator's first "मैं" or "सवाल है" voice, planting a thesis sentence. Echo that sentence verbatim near the end. The title appears as an overlay of 2 s or less on its last words, not as a black card.
3. **Channel intro (3.0 s).** The locked Curious India intro (`brand.intro` in `channel.yaml`) runs straight after the promise. The script reserves the gap with `pause_after_seconds: 3.0` on the promise section and records it in `metadata.channel_intro`.
4. **The video.** Background starts only after the first re-hook and answers a question the viewer now holds (45 s at most, at least three visual changes); tell it as a story first (a person, a date), not as a definition. Each section then escalates on the last, with a curiosity beat every 20-40 s and a new evidence artefact every ~20 s for the first two minutes. If you use open loops, carry them as on-screen chips that pay off later; never as a spoken list.
5. **Landing.** The thesis echo, a callback to the opening evidence, and a **closing binary policy question** in the last ~75 s: a concrete A/B tied to the video's evidence, held on screen for ~25 s, with a payoff promise ("दोनों तरफ़ की सबसे दमदार दलीलें मैं अगले वीडियो में पढ़ूँगा"). It must force a trade-off and ask for one reason; "आप क्या सोचते हैं?" does not count.
6. **Publish.** One pinned starter comment carries the question (YouTube allows a single pin), with the comment rules in it and "Hold potentially inappropriate comments for review" on. Sources go in the description with timestamps. Reply to the first ~10 comments in the first hour and heart the best argument on each side.

Skip origin stories and background the audience already knows.

## Shorts structure (45-60 s)

Same narrator, same "आप" register, compressed. There is no teaser, no title card and no channel intro; the logo appears as an end-bug on the last 2 s (`brand.intro.shorts` in `channel.yaml`).

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
- In long-form, reserve **3.0 s of narration-free time** for the channel intro; it is not speaking time, so the final video runs about 3 s longer than the narration.
- Write in section-sized chunks aligned to narrative beats. Each chunk carries its `delivery_cues.provider_text` with eleven_v3 audio tags: `[curious]`, `[sighs]`, `[whispers]`, `[mischievously]`, `[sarcastic]`, `[serious]`, `[pause]`, and others.
- Before any TTS spend, deliver a tagged-script HTML/MD for review. Then render 1-2 sample sections at the riskiest tonal pivot and get a listen-and-approve.
- After a direct-address or tag pass, re-run the `skills/meta/script-reviewer.md` consistency check: `text` vs `provider_text`, and `emphasis_words` present verbatim.

## Hooks

Work well here:
- A document set against reality: a court order and the number of cases still running under it; a stated reason and the day it expired.
- A concrete, strange fact: "कल्पना कीजिए…" followed by a number that shouldn't be true.
- A myth stated confidently, then cracked.

Avoid "नमस्कार दोस्तों", "welcome back", or any preamble before the mystery.

## Humor

Medium. Look for irony, bureaucratic absurdity and relatable comparisons, especially in dry, statistical sections. The comic energy belongs to the absurdity beats. Pivot hard to grave and respectful the moment real human cost enters the story.

## Never

- Jargon before its analogy.
- Mocking victims or communities.
- An AI face of a real named person.
- Exact text (numbers, dates, names) baked into a generated image.
- A spoken list of questions before the story, or background and definitions before 0:45.
- A closing question that is not an A/B with a reason attached.
