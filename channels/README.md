# Channel Profiles

Each folder here is one YouTube channel. A channel's profile holds the defaults every video on that channel starts from. The agent loads it before the proposal stage, so a product-review Short doesn't inherit the long-form explainer's voice.

```
channels/<id>/
  channel.yaml      # structured defaults: language, formats (long_form / shorts), pipeline, playbook, voice, script, visuals, music, policies
  script-guide.md   # prose rules for this channel's scripts: register, a structure per format, examples
  characters.md     # optional character bible: recurring cast, locked appearance and voices
  cast/             # optional structured bible (visuals.cast_dir): cast.yaml + <character>/character.yaml + refs/
```

A **structured bible** (`cast/`) holds each character's locked text, plus approved reference images (master, turnaround, outfits, poses, expressions). `lib/character_bible.py` builds every character prompt from it. See [`skills/meta/character-bible.md`](../skills/meta/character-bible.md); the template is in `_template/cast/`.

Every channel publishes both **long-form (16:9)** and **Shorts (9:16)**. Each production picks one, and the profile's `formats` block sets that format's length, structure, build mode and pacing.

| Channel | Language | Long-form | Shorts | Pipeline | Playbook |
|---|---|---|---|---|---|
| `explainer` (Curious India) | Hindi | 10-15 min | 45-60 s | `animated-explainer` | `vox-explainer` |
| `cinematic` | Hinglish | 10-20 min | 45-60 s | `cinematic` | `cinematic-documentary` |
| `story-toons` (Kids Story) | Hinglish | 4-8 min | 40-60 s | `character-animation` | `toon-story` |
| `product-review` | Hinglish | 8-12 min | 40-60 s | `hybrid` (with alternates) | `tech-review` |
| `rani-ai` | Hinglish | 5-10 min | 20-45 s (plus Reels) | `cinematic` | `lifestyle-reel` |
| `young-story` (Young Story) | Hinglish | 8-15 min | 45-60 s | `animation` | `anime-drama` |

## How the agent uses a profile

See [`skills/meta/channel-profiles.md`](../skills/meta/channel-profiles.md). In short:

- **Which channel and format.** Each production belongs to one channel and is either long-form or a Short. If the request doesn't say, the agent asks.
- **Pre-filling.** The profile pre-fills the proposal: pipeline, playbook, voice, build mode and runtime recommendation, music. It also feeds the script guide to the script stage and the character bible to the asset stage.
- **Defaults only.** Approval gates, showing both composition runtimes, announcing paid calls and approving AI video each time all still apply.
- **Where new preferences go.** A preference you set for a channel goes into that channel's files here, not into global defaults.
- **Open questions.** `open_questions` lists defaults you still need to confirm. The agent raises them at that channel's next proposal.

## Add a channel

1. Copy `_template/` to `channels/<new-id>/`. The id is kebab-case and must match the folder name.
2. Fill in `channel.yaml` and `script-guide.md`. If the channel has recurring characters, keep `cast/` and set `visuals.cast_dir: cast` (structured bible, best for story channels), or add a prose `characters.md`. Otherwise delete the copied `cast/` folder.
3. Validate it:
   ```
   python -c "from lib.channel_profile import load_channel; load_channel('<new-id>'); print('ok')"
   ```
   The loader checks the schema (`schemas/channels/channel_profile.schema.json`). It also checks that the playbook, pipelines, media profile and referenced files all exist.
4. Add a row to the table above.

`tests/contracts/test_channel_profiles.py` validates every channel folder.
