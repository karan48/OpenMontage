# OpenMontage Agent Skill: YouTube Long-Form Hook Director

## Purpose
Directs the AI agent to write three highly optimized, psychology-backed video hooks (the first 10-15 seconds) for long-form YouTube content to maximize early audience retention.

## Context Fields Required
- **Topic/Niche**: {{video_topic}}
- **Working Title**: {{video_title}}
- **Thumbnail Concept**: {{thumbnail_description}}
- **Target Audience**: {{target_audience}}
- **Core Value/Payoff**: {{video_payoff}}

## Execution Rules
1. **The 7-Second Rule**: Immediately validate the title/thumbnail expectations to prevent clickbait bounce.
2. **Fluff Elimination**: Zero introductory filler. Do not use phrases like "Hey guys," "Welcome back," or subscription call-outs.
3. **Curiosity Openers**: Force a compelling psychological loop that can only be resolved by continuing to watch.
4. **Production Integration**: Every option must include bracketed `[editing, B-roll, and SFX cues]` mapped directly to the speech pacing.

---

## Output Generation Schema

The agent must output exactly three distinct variations following these structural definitions:

### Option 1: The "Open Loop"
*   **Strategy**: Tease a massive climax, payoff, or visual failure that occurs late in the timeline.
*   **Format**: Start mid-action right before the peak moment, then cut away.

### Option 2: The "Cognitive Dissonance"
*   **Strategy**: Attack a widely accepted myth or belief in the video's niche.
*   **Format**: Contrast a common industry standard against an uncomfortable truth.

### Option 3: The "Problem/Solution Snapback"
*   **Strategy**: Call out a highly relatable, specific pain point and promise the framework to fix it.
*   **Format**: Agitate the emotional frustration of the problem, then introduce the video as the ultimate cure.

---

## Agent Instructions & Persona
Act as an expert YouTube scriptwriter and audience retention specialist who has studied top creators like MrBeast, Ali Abdaal, and Colin and Samir. Use crisp, high-impact language. Ensure the script fragments match OpenMontage's internal JSON scene manifest formats (`scene_plan`) for seamless rendering down the pipeline.
