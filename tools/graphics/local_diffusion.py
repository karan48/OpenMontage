"""Local Stable Diffusion image generation via diffusers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class LocalDiffusion(BaseTool):
    name = "local_diffusion"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "local_diffusion"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.LOCAL_GPU

    dependencies = []  # checked dynamically
    install_instructions = (
        "Install diffusers for local Stable Diffusion:\n"
        "  pip install diffusers transformers accelerate torch"
    )
    agent_skills = []

    capabilities = ["generate_image", "generate_illustration", "text_to_image", "image_to_image"]
    supports = {
        "negative_prompt": True,
        "seed": True,
        "offline": True,
        "custom_size": True,
        "input_image": True,
        "hero_reference": True,
        "lora": True,
    }
    best_for = [
        "offline/air-gapped generation",
        "free image generation (no API cost)",
        "privacy-sensitive workflows",
        "hero-reference character consistency (pass input_image)",
    ]
    not_good_for = [
        "CPU-only machines (very slow)",
        "highest quality output (API models are better)",
        "identity-exact character consistency across very different poses (use img2img strength tuning + expect drift; for guaranteed identity use a rigged character-animation path instead)",
    ]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "negative_prompt": {"type": "string", "default": ""},
            "width": {"type": "integer", "default": 512},
            "height": {"type": "integer", "default": 512},
            "model": {
                "type": "string",
                "default": "stabilityai/stable-diffusion-2-1-base",
            },
            "seed": {"type": "integer"},
            "num_inference_steps": {"type": "integer", "default": 30},
            "guidance_scale": {"type": "number", "default": 7.5},
            "input_image": {
                "type": "string",
                "description": "Path to a hero/reference image. When set, runs image-to-image so the output stays visually consistent with this reference (e.g. a locked character).",
            },
            "strength": {
                "type": "number",
                "default": 0.6,
                "description": "Only used with input_image. 0-1; lower keeps more of the reference (more consistent, less prompt influence), higher lets the prompt change more (less consistent).",
            },
            "lora_path": {
                "type": "string",
                "description": "Path to a .safetensors LoRA file (e.g. a trained character identity). Must match the architecture of `model` (SD1.5 LoRA needs an SD1.5 model, SDXL LoRA needs an SDXL model, etc).",
            },
            "lora_scale": {
                "type": "number",
                "default": 0.8,
                "description": "Only used with lora_path. 0-1 weight of the LoRA's influence; lower blends more with the base model, higher enforces the trained identity more strongly.",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=2, ram_mb=8000, vram_mb=4000, disk_mb=5000, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=1)
    idempotency_key_fields = [
        "prompt", "width", "height", "seed", "model", "input_image", "strength", "lora_path", "lora_scale",
    ]
    side_effects = ["writes image file to output_path", "may download model weights on first run"]
    user_visible_verification = ["Inspect generated image for relevance and quality"]

    def get_status(self) -> ToolStatus:
        try:
            import diffusers  # noqa: F401
            return ToolStatus.AVAILABLE
        except ImportError:
            return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        return 30.0  # ~30s on a mid-range GPU

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(
                success=False,
                error="diffusers not installed. " + self.install_instructions,
            )

        import torch
        from diffusers import StableDiffusionImg2ImgPipeline, StableDiffusionPipeline
        from PIL import Image

        start = time.time()
        prompt = inputs["prompt"]
        negative = inputs.get("negative_prompt", "")
        width = inputs.get("width", 512)
        height = inputs.get("height", 512)
        seed = inputs.get("seed")
        model_id = inputs.get("model", "stabilityai/stable-diffusion-2-1-base")
        steps = inputs.get("num_inference_steps", 30)
        guidance = inputs.get("guidance_scale", 7.5)
        input_image_path = inputs.get("input_image")
        strength = inputs.get("strength", 0.6)
        lora_path = inputs.get("lora_path")
        lora_scale = inputs.get("lora_scale", 0.8)

        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if device == "cuda" else torch.float32

            generator = None
            if seed is not None:
                generator = torch.Generator(device=device).manual_seed(seed)

            if input_image_path:
                pipe = StableDiffusionImg2ImgPipeline.from_pretrained(model_id, torch_dtype=dtype)
            else:
                pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=dtype)
            pipe = pipe.to(device)

            cross_attention_kwargs = None
            if lora_path:
                pipe.load_lora_weights(lora_path)
                cross_attention_kwargs = {"scale": lora_scale}

            if input_image_path:
                init_image = Image.open(input_image_path).convert("RGB").resize((width, height))

                image = pipe(
                    prompt,
                    image=init_image,
                    negative_prompt=negative,
                    strength=strength,
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                    generator=generator,
                    cross_attention_kwargs=cross_attention_kwargs,
                ).images[0]
            else:
                image = pipe(
                    prompt,
                    negative_prompt=negative,
                    width=width,
                    height=height,
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                    generator=generator,
                    cross_attention_kwargs=cross_attention_kwargs,
                ).images[0]

            output_path = Path(inputs.get("output_path", "generated_image.png"))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(output_path))

        except Exception as e:
            return ToolResult(success=False, error=f"Local diffusion generation failed: {e}")

        return ToolResult(
            success=True,
            data={
                "provider": "local_diffusion",
                "model": model_id,
                "prompt": prompt,
                "output": str(output_path),
                "mode": "image_to_image" if input_image_path else "text_to_image",
                "input_image": input_image_path,
                "lora_path": lora_path,
                "lora_scale": lora_scale if lora_path else None,
            },
            artifacts=[str(output_path)],
            cost_usd=0.0,
            duration_seconds=round(time.time() - start, 2),
            seed=seed,
            model=model_id,
        )
