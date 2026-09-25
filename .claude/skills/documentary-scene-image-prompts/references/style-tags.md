# Style Tags

Append the chosen style tag verbatim to the end of **every** prompt in a project. Pick once per project and keep it — changing mid-video breaks visual continuity. If the user switches style, re-issue affected prompts with the new tag rather than mixing.

Aspect ratio: append `16:9` (YouTube) or `9:16` (Shorts/Reels/TikTok) in whatever syntax the target tool uses (e.g. `--ar 16:9` for Midjourney, or a plain "16:9 aspect ratio" phrase for tools that take natural language).

## Presets

### Photorealistic documentary (default)
```
photorealistic documentary photograph, natural available light, shallow depth of field, 35mm lens, subtle film grain, muted realistic color grading, historically accurate details, cinematic composition, high detail
```

### Archival / period photograph
For history pieces where images should feel like they came from the era. Specify the decade in the scene text.
```
authentic archival photograph, period-accurate black and white film, soft focus edges, visible grain and slight fading, documentary press photography style, natural lighting, high detail
```

### Acrylic painting
```
expressive acrylic painting, visible confident brushstrokes, rich layered textures, warm earthy palette with bold accents, painterly editorial illustration style, dramatic but soft lighting, fine art quality
```

### Watercolor illustration
```
delicate watercolor illustration, soft washes and bleeding edges, textured cold-press paper, restrained muted palette, loose linework, gentle natural light, storybook documentary feel
```

### Cinematic noir
For true crime, espionage, or tense political material.
```
cinematic film noir still, high-contrast chiaroscuro lighting, deep shadows, moody desaturated palette with cool tones, atmospheric haze, anamorphic lens, dramatic composition, high detail
```

### 2D animated explainer
Pairs with the `vox-explainer` style playbook for flat, graphic explainer videos.
```
clean flat 2D vector illustration, bold simple shapes, limited harmonious palette, subtle paper texture, minimal shading, clear silhouettes, modern editorial explainer animation style
```

### Graphic novel
```
graphic novel panel illustration, bold ink linework, cross-hatched shading, limited color palette with strong accents, dramatic angles, detailed backgrounds, cinematic comic art
```

### 3D stylized
```
stylized 3D render, soft global illumination, clay-like materials, gentle depth of field, warm cinematic lighting, clean composition, Pixar-inspired documentary diorama
```

## Negative prompt boilerplate

For tools that accept a negative prompt (Stable Diffusion, FLUX via some front-ends, etc.), use this as the base and add style-specific exclusions:

```
text, watermark, logo, signature, captions, subtitles, blurry, low resolution, jpeg artifacts, distorted faces, extra fingers, malformed hands, extra limbs, duplicated people, cropped heads, oversaturated, cartoonish (for photoreal styles), gore, graphic violence, nudity
```

For tools without a negative-prompt field (Midjourney uses `--no`, DALL-E / Nano Banana have none), fold the most important exclusions into the prompt as positives instead — e.g. "no visible text", "anatomically correct hands".

## Tips

- Keep era details in the scene text, not the style tag, so one tag works across a whole project spanning multiple decades.
- Hindi/Indian subject matter: name the region and period concretely (e.g. "1947 Punjab railway platform") — generic "Indian" prompts drift toward stereotyped imagery.
- If an image tool keeps rendering text on signs/documents, add "illegible or no text" to the scene description.
