# Cast Bible: Kids Story

Locked designs for the recurring cast. **Reuse everything here verbatim.** Small rewordings between episodes are how characters drift.

## How the cast is built and reused

1. **Episode 1** runs the full `character-animation` pipeline: `character_design`, then `rig_plan` and `pose_library`, then the sample. Once you approve a character, copy its approved artifacts and rig files to `channels/story-toons/cast/<character-id>/`:
   - `character_design.json`
   - `rig_plan.json`
   - `pose_library.json`
   - the SVG rig
2. **Every later episode** sets the proposal's `reuse_strategy` to "reuse channel cast". It loads the rigs from `cast/` and skips redesign. Its `character_design` stage confirms the existing cast instead of inventing a new one.
3. **A new recurring character** is added here and designed once before it appears in an episode.

## Style anchors (all characters)

- Flat vector fills with thick rounded dark outlines (#1F1B16) and one soft cel-shadow tone.
- Big readable silhouettes. Heads are slightly large for clear expressions at phone size.
- Colours come from the `toon-story` palette: orange #FF6B35, blue #3A86FF, yellow #FFD23F, purple #7B2CBF, on cream #FFF8EC.

## Cast

*None yet. Designed on episode 1.* Use this entry format:

```
### <Name> (<character-id>)
- Role: lead | sidekick | recurring
- Age / look: ...
- Locked design: outfit, colours, hair, accessories (verbatim)
- Personality: ...
- Catchphrase (optional): ...
- Voice: provider, voice_id, settings, sample line
- Signature poses / actions: ...
```
