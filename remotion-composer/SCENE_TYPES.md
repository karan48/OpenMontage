# Remotion Composer — Scene & Overlay Cheat Sheet

Authoritative list of `cut.type` and `overlay.type` values the `Explainer` composition accepts. Each row maps to a dispatch case in `src/Explainer.tsx`.

When you add a new component, append it here and in `src/components/index.ts`.

---

## Cut types (`cut.type`)

| `type` | Component | Required fields | Common fields | Purpose |
|---|---|---|---|---|
| *(none — video)* | `OffthreadVideo` | `source` (path to mp4) | `source_in_seconds`, `animation` (zoom-in, ken-burns), `in_seconds`, `out_seconds` | Play an MP4 clip directly |
| *(none — image)* | `Img` | `source` (path to png/jpg) | `animation`, `in_seconds`, `out_seconds` | Play a still with Ken Burns |
| `text_card` | `TextCard` | `text` | `fontSize`, `backgroundVideo`, `backgroundOverlay`, `color` | Large-typography beat |
| `hero_title` | `HeroTitle` | `text` | `heroSubtitle`, `backgroundVideo`, `backgroundOverlay` | Title/end card |
| `stat_card` | `StatCard` | `stat` | `subtitle`, `accentColor`, `backgroundVideo` | A single big number |
| `callout` | `CalloutBox` | `text` | `callout_type` (info/warning/tip/quote), `title`, `backgroundVideo` | Boxed message with bullets |
| `comparison` | `ComparisonCard` | `leftLabel`, `leftValue`, `rightLabel`, `rightValue` | `title`, `backgroundColor` | Side-by-side compare |
| `bar_chart` | `BarChart` | `chartData` | `chartAnimation`, `showValues`, `showGrid`, `backgroundVideo` | Animated bars |
| `line_chart` | `LineChart` | `chartSeries` | `chartAnimation`, `xLabel`, `yLabel`, `showMarkers` | Animated line |
| `pie_chart` | `PieChart` | `chartData` | `donut`, `centerLabel`, `centerValue`, `showLegend` | Pie / donut |
| `kpi_grid` | `KPIGrid` | `chartData` | `title`, `columns`, `chartAnimation` | 2–4 column KPI grid |
| `progress_bar` | `ProgressBar` | `progress` | `progressLabel`, `progressColor`, `progressSegments` | Animated progress |
| `anime_scene` | `AnimeScene` | `images` (list) | `cues`, `particles`, `lightingFrom`, `lightingTo`, `vignette` | Still-image anime scene with particles + camera motion. **`cues`** (`[{image, at, fade?}]`, seconds from the cut start) switch images at exact times, for example word-timed expression changes, blinks and mouth movements from forced alignment. `images[0]` shows until the first cue; each cue fades its image in on top of the previous one (no dip), default 0.25 s, 0 = hard cut. Without `cues`, rendering is unchanged. Each cut fades in from its own `backgroundColor` (opaque navy by default), so back-to-back cuts dip to near-black; for soft crossfades overlap the previous cut ~0.3 s and give the incoming cut `backgroundColor: "transparent"`. Multi-image cuts dissolve over 1.2 s — different compositions read as a muddy double exposure, so use near-identical variants only. |
| **`terminal_scene`** | **`TerminalScene`** | **`steps`** (list of cmd/out/pause/pill) | **`terminalTitle`, `prompt`, `accentColor`** | **Synthetic terminal animation — NO real capture needed. See [`.agents/skills/synthetic-screen-recording/SKILL.md`](../.agents/skills/synthetic-screen-recording/SKILL.md)** |
| **`screenshot_scene`** | **`ScreenshotScene`** | **`backgroundImage`** (path in `public/`), **`screenshotSteps`** (list of overlays) | **`screenshotSize` (natural px w/h), `cursorStartAt`, `accentColor`** | **Approach-1 synthetic UI — drop any screenshot, animate scripted overlays on top (cursor, click_pulse, type_into, bubble_append, typing_dots, highlight_box, callout_balloon). Viewer-indistinguishable from a real recording for 15–30s focused demos. Coordinates are normalized (0–1) against the contain-fit rect. See [`.agents/skills/synthetic-ui-recording/SKILL.md`](../.agents/skills/synthetic-ui-recording/SKILL.md) (planned).** |
| **`phone_chat`** | **`PhoneChat`** | `phoneLayout` (`full` \| `split` \| `pill`); `contactName` + `chatSteps` (full/pill) or `chatLanes` (split) | `chatHistory`, `chatInitialStatus`, `phoneBackdrop` (+`phoneBackdropBlur`, `phoneBackdropDim`), `counterLabel`/`counterStart`, `clockText`, `entrance` (`none` for frame 1), `accentColor` | **Story beats told through texts: a generic messenger screen (no real app branding) that types, deletes, shows/hides the header "typing…" status, pulses Send under a hovering thumb, ticks a story counter ("Drafts: 47") and appends bubbles. Steps: `type{text,cps}`, `delete{chars?,cps}`, `status{typing\|online\|none}`, `send_hover{seconds}`, `counter{value}`, `bubble{side,text}`, `pause{seconds}`, run in order from the cut start. `split` stacks two headers whose statuses toggle independently; `pill` floats "Name · typing…" over a full-bleed image. Devanagari-safe (Poppins + Hind). First used by young-story-short-01.** |

---

## Caption options (`captionOptions`, top-level prop)

Word captions (`captions`) render with the legacy defaults unless `captionOptions` is set: `wordsPerPage` (6), `fontSize` (42), `fontFamily`, `bottomPercent` (distance from the bottom as % of height; ~22-26 keeps 9:16 captions above the Shorts UI), `breakOnGapMs` (start a new page at a pause or speaker change), `holdAfterMs` (clear a page this long after its last word instead of holding it to the next page). For Hindi/Hinglish use `fontFamily: "Hind, Poppins, sans-serif"` (both are loaded by `PhoneChat`).

---

## Overlay types (`overlay.type`)

| `type` | Component | Required fields | Common fields | Purpose |
|---|---|---|---|---|
| `section_title` | `SectionTitle` | `text` | `accentColor`, `position` (top-left, etc.) | Tiny section label |
| `stat_reveal` | `StatReveal` | `text` | `subtitle`, `accentColor`, `position` | Corner stat badge |
| `hero_title` | `HeroTitle` (as overlay) | `text` | `subtitle` | Full-frame title overlay |
| **`provider_chip`** | **`ProviderChip`** | **`providers`** (list of strings) | **`cycleSeconds`, `position`, `accentColor`, `label`** | **Rotating badge that cycles through provider names — used in AI-generated-motion scenes to show which model produced the clip** |

---

## Adding a new scene type

1. Create the React component in `src/components/MyScene.tsx`. Use `interpolate(frame, [inFrame, outFrame], [from, to])` and `spring(...)` for motion. Read `useCurrentFrame()` and `useVideoConfig()`.
2. Export it in `src/components/index.ts`.
3. Add the `type` to the `Cut` interface in `src/Explainer.tsx` (and any new prop fields).
4. Add a dispatch case in `SceneRenderer`:
   ```tsx
   if (cut.type === "my_scene" && cut.mySceneData) {
     return maybeWrapWithBg(<MyScene ... />);
   }
   ```
5. Document it in this file. That's what makes it discoverable to the next agent.

## Existing synthetic-UI components

Currently only `TerminalScene` exists. The pattern generalizes — likely candidates to add next, if a pipeline needs them:

- `ChatTranscript` — Claude/Cursor/GPT chat-bubble timeline with typing animation
- `EditorScene` — VS Code-style code editor with syntax highlight + cursor motion
- `PrReview` — GitHub PR diff view with inline-comment reveals
- `SlackThread` — Slack thread with avatars + reaction pops
- `TicketBoard` — Jira / Linear card moving across columns

Pattern: follow `TerminalScene.tsx` — a `steps` list of timeline primitives, cursor-advancing durations, spring-based reveals, optional non-blocking pills/badges.
