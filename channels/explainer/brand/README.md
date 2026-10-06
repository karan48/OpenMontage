# Curious India — brand assets (locked)

These files are the channel's brand identity. Treat them like a logo file: **the same clip in every video, never restyled, regenerated or re-timed per video**, and never turned into a reusable scene component. How productions use them is in `skills/meta/channel-profiles.md` → "Brand intro and standing structure"; the contract is the `brand` block in `../channel.yaml`.

Status (2026-10-05): the picture is final. The sting is **provisional (candidate A)** until the owner picks between candidates A, B and C; swapping it is a re-mux (see below), nothing else changes.

| File | What it is |
|---|---|
| `logo.jpg` | The YouTube channel logo, 600×600 (copy of `../YT-Thumbnail.jpg`) |
| `logo_circle.png` | 584×584 RGBA, circle-masked (radius 292 about the fitted centre, so the JPEG's white fringe is gone). Used by the intro and by the Shorts end-bug. Never scale it above ~1.03× — the source is only 600 px |
| `intro_16x9.mp4` | The long-form intro: 1920×1080, 30 fps, **3.000 s**, H.264 + AAC 48 kHz stereo, with the sting |
| `intro_sting.wav` | The same sting as a stand-alone 24-bit 48 kHz WAV. Compositions play the MP4 muted and schedule this in the mix |
| `intro_sting_short.wav` | 1.2 s cut of the sting for the Shorts end-bug |
| `curious-india-intro/` | Remotion source (`index.tsx`, `Root.tsx`, `Intro.tsx`), hand-authored, no stock-registry imports |

## The intro (picture)

Ink-black field; a saffron hairline from the left and a green hairline from the right draw in (0–0.33 s); the circular badge iris-reveals while it settles 0.92 → 1.0 (0.13–0.8 s); one bulb-glow pulse at 1.0–1.67 s (peak 1.2 s); a soft light sweep crosses the badge (1.53–2.2 s) over a slow 3% push-in; fade to black 2.73–2.97 s. Saffron and green ambient glows echo the logo's two arcs.

## The sting (audio)

Instrumental, no voice. Each candidate is a 3.0 s ElevenLabs sound generation (`eleven_text_to_sound_v2`, `prompt_influence` 0.6), trimmed of leading silence, delayed so its main hit meets the picture, fitted to exactly 3.000 s with a 0.25 s fade-out, and gained so the **momentary max is −18 LUFS with peaks ≤ −6 dBFS** (the narration-free-gap level from the SFX mixing notes; narration sits at −17 LUFS integrated).

| | Prompt | Delay | Feel |
|---|---|---|---|
| A | "A short elegant logo sting for a documentary channel, 3 seconds: a soft airy whoosh rising into a warm low bloom, then one bright glockenspiel bell ping, ending in a gentle shimmering tail that fades out. Clean, no drums, no vocals." | 0.30 s | riser, hit as the glow starts |
| B | "A short logo sting, 3 seconds: a soft santoor shimmer rising into one clear bell-like santoor note, a single soft tabla tap, then a delicate resonant tail fading out. Warm and elegant, no vocals." | 0.80 s | silence, then a pluck as the badge locks |
| C | "A modern minimal logo sting, 3 seconds: a soft riser, then a clean plucked synth note with a short bright sparkle, ending in a smooth airy tail that fades out. No drums, no vocals." | 0.15 s | immediate synth hit with the iris |

## Shorts

No intro. The last 2 s of every Short carry `logo_circle.png` as a small end-bug (safe zone: keep it out of the bottom 20% and right 15%) with `intro_sting_short.wav`.

## Re-rendering the picture

1. Stage the source into the composer tree (mirrors `video_compose._stage_atelier_project`): copy `curious-india-intro/*.tsx` to `remotion-composer/projects/curious-india-intro/`.
2. From `remotion-composer/`:
   `npx remotion render projects/curious-india-intro/index.tsx CuriousIndiaIntro <abs path>/intro_silent.mp4 --public-dir=<abs path to this brand/ folder> --crf=18 --concurrency=4 --port=3977`
   The explicit `--port` matters: if another app holds `:3000` (a NestJS service did on 2026-10-05) Remotion's bundle server collides with it and fails with "Cannot GET /index.html".
3. Mux the sting with an **explicit stream map** — Remotion's "silent" render still carries a silent audio track, and without `-map` ffmpeg keeps that one:
   `ffmpeg -i intro_silent.mp4 -i intro_sting.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -ar 48000 -shortest intro_16x9.mp4`

Swapping the sting after the owner's pick: regenerate `intro_sting.wav` and `intro_sting_short.wav` from the chosen candidate with the delays and levels above, then repeat step 3 and update `status` in `../channel.yaml`.

## Verify after any change

`ffprobe` the MP4 (3.000 s, 1920×1080, 30 fps, one video + one audio stream); `ebur128` on the WAV (momentary max −18 LUFS, peak ≤ −6 dBFS); view stills at 0.2, 0.5, 1.0, 1.2, 1.8, 2.9 s; then `python -c "from lib.channel_profile import load_channel; load_channel('explainer')"`.
