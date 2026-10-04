# Character Bible: Young Story

Locked descriptions for recurring characters. **Paste each description verbatim into every prompt the character appears in.** `flux_image` is text-to-image only, so consistency comes entirely from identical wording. Small rewordings between scenes are how faces drift.

## Style anchors (all characters)

- Modern anime film still: clean line art, soft cel shading, detailed painted Indian backgrounds.
- Characters in romantic storylines are adults (18+), drawn with adult proportions, never chibi or childlike.
- Casual, modest Indian college wear: kurtas, tees, jeans, hoodies, salwar suits, sneakers.
- Colours come from the `anime-drama` palette: dusk blue #5B6CFF, sakura pink #FF8FA3, golden amber #FFC56E, on twilight navy #0E1022.

## Recurring cast

*None yet. Created with the first story.* Use this entry format:

```
### <Name> (<character-id>)
- Role: lead | love interest | best friend | rival | parent | recurring
- Age: (18+ for anyone in a romantic storyline)
- Locked description (verbatim in every prompt): face shape, eyes, hair (length, colour, style), skin tone,
  build, signature outfit and colours, one signature accessory
- Personality: ...
- How they talk: register, slang, catchphrase
- Voice: provider, voice_id, settings, sample line
- Stories appeared in: ...
```

If drift persists for a lead across episodes, consider training a character LoRA, as was done for Rani in `channels/rani-ai/`.
