# Character Bible: Rani_ai

Locked identity for the channel's persona. **Reuse everything here verbatim in every prompt.** Never let the model reinterpret her build, hair or accessories from shot to shot.

## Identity

- **On-screen name:** Rani (channel: Rani_ai). Use "Rani" in all narration, captions and titles.
- **LoRA trigger word:** `Amita`. It must appear verbatim in every generation prompt or the LoRA won't activate. Never put "Rani" in a generation prompt.
- **LoRA file:** `D:\work\AI Model\Amita\Lora\amita_flex_lora_v1.safetensors`
  - Base model: `ostris/Flex.1-alpha` (FLUX family), ai-toolkit, 3000 steps, linear rank 32.
  - Pass it as `lora_path` to `flux_image`. It uploads to fal storage and routes to `fal-ai/flux-lora`, at about $0.035 per image.
  - `flux_image` is text-to-image only, with no reference-image conditioning, so consistency comes entirely from the locked text below.
- **Voice:** not chosen yet. After the audition, record the provider, voice_id, settings and a sample line here.

## Canonical appearance block (paste verbatim)

> Amita, a woman in her late twenties with a curvy, moderately plus-size build (softly rounded figure, not overly heavy — a healthy medium-plus size, not thin and not full-figured), long dark wavy hair worn loose, a small nose stud, small gold drop earrings, wearing a solid deep maroon long-sleeve top with a modest round neckline (fully covering the chest, no cleavage), tucked into high-waisted maroon trousers with a matching fabric belt defining her waist, monochrome maroon outfit, soft flowy fabric, paired with a delicate gold necklace

Locked 2026-07-15. The reference image is `sc12.png` from the `body-positivity-confidence-20s` project.

**Expected variance.** The same wording sometimes renders her visibly heavier than `sc12.png`. That is run-to-run variance, not a wording failure. Flag the image for a regen rather than rewording the block.

## Wardrobe variations

Use these only when a scene needs a change from the locked look.

Keep the same build, hair and accessories. Choose the outfit with this checklist (from the "Styling Tips for Curvy Girls" reference):

1. **Define the waist** with a belt, tie-up or wrap.
2. **Modest neckline.** Prefer round, boat or scoop necklines with separates. Wrap-style V-necks render too plunging no matter how they are worded.
3. **High-waist bottoms.**
4. **Soft, flowy, breathable fabric.**
5. **One dominant colour** (monochrome).
6. **A statement accessory:** earrings, a long necklace or a structured bag.
7. **Wear what she loves.** Confidence is the outfit.

A deliberate change for a real time-of-day beat is fine. For example, loose modest sleepwear for a waking-up shot. It still uses the same build and the principles above.

## Hard rules

- Casual, modest clothing only. No intimate or revealing wardrobe in any context.
- Any image made before 2026-07-15 with the old "average build / buttoned kurta" description is stale. Regenerate it if you reuse it.
