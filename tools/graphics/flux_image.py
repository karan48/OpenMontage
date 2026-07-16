"""FLUX image generation via fal.ai API."""

from __future__ import annotations

import os
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


class FluxImage(BaseTool):
    name = "flux_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "flux"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.API

    dependencies = ["fal-client"]  # checked dynamically via env var; fal-client only needed for local lora_path uploads
    install_instructions = (
        "Set FAL_KEY to your fal.ai API key.\n"
        "  Get one at https://fal.ai/dashboard/keys\n"
        "  For custom LoRA uploads from a local file, also: pip install fal-client"
    )
    agent_skills = ["flux-best-practices", "bfl-api"]

    capabilities = ["generate_image", "generate_illustration", "text_to_image"]
    supports = {
        "negative_prompt": True,
        "seed": True,
        "custom_size": True,
        "lora": True,
    }
    best_for = [
        "photorealistic images",
        "general-purpose image generation",
        "high quality at low cost (~$0.03/image)",
        "consistent custom character via a trained FLUX LoRA (lora_path/lora_url)",
    ]
    not_good_for = ["text rendering in images", "offline generation"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "negative_prompt": {"type": "string", "default": ""},
            "width": {"type": "integer", "default": 1024},
            "height": {"type": "integer", "default": 1024},
            "model": {
                "type": "string",
                "enum": ["flux-pro/v1.1", "flux/dev", "flux-pro"],
                "default": "flux-pro/v1.1",
                "description": "Ignored when a LoRA is supplied — LoRA requests always route to the fal-ai/flux-lora endpoint (FLUX.1 dev based).",
            },
            "seed": {"type": "integer"},
            "num_inference_steps": {"type": "integer"},
            "guidance_scale": {"type": "number"},
            "lora_path": {
                "type": "string",
                "description": "Local path to a FLUX .safetensors LoRA file. Uploaded to fal.ai storage automatically (requires fal-client installed). Use lora_url instead if it's already hosted.",
            },
            "lora_url": {
                "type": "string",
                "description": "URL to an already-hosted FLUX LoRA .safetensors file. Takes priority over lora_path if both are set.",
            },
            "lora_scale": {
                "type": "number",
                "default": 1.0,
                "description": "Only used with lora_path/lora_url. Weight of the LoRA's influence on the output.",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=100, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "width", "height", "seed", "model", "lora_path", "lora_url", "lora_scale"]
    side_effects = ["writes image file to output_path", "calls fal.ai API"]
    user_visible_verification = ["Inspect generated image for relevance and quality"]

    def _get_api_key(self) -> str | None:
        return os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY")

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        if inputs.get("lora_path") or inputs.get("lora_url"):
            return 0.035  # fal-ai/flux-lora, dev-tier pricing
        model = inputs.get("model", "flux-pro/v1.1")
        if "pro" in model:
            return 0.05
        return 0.03  # dev tier

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="No fal.ai API key found. " + self.install_instructions,
            )

        import requests

        start = time.time()
        model = inputs.get("model", "flux-pro/v1.1")
        prompt = inputs["prompt"]
        width = inputs.get("width", 1024)
        height = inputs.get("height", 1024)
        lora_path = inputs.get("lora_path")
        lora_url = inputs.get("lora_url")
        lora_scale = inputs.get("lora_scale", 1.0)

        if lora_path and not lora_url:
            try:
                import fal_client
                from fal_client.client import MultipartUpload

                os.environ.setdefault("FAL_KEY", api_key)
                client = fal_client.sync_client
                if os.path.getsize(lora_path) > 100 * 1024 * 1024:
                    # fal-client's default concurrent multipart upload (10 parallel
                    # connections) reliably drops mid-transfer on some networks
                    # ("Server disconnected without sending a response"). A single
                    # connection with smaller chunks is slower but survives.
                    lora_url = MultipartUpload.save_file(
                        file_path=lora_path,
                        client=client._get_cdn_client(),
                        token_manager=client._token_manager,
                        content_type="application/octet-stream",
                        chunk_size=5 * 1024 * 1024,
                        max_concurrency=1,
                    )
                else:
                    lora_url = fal_client.upload_file(lora_path)
            except ImportError:
                return ToolResult(
                    success=False,
                    error="lora_path given but fal-client isn't installed. "
                    "pip install fal-client (or pass an already-hosted lora_url instead).",
                )
            except Exception as e:
                return ToolResult(success=False, error=f"Failed to upload LoRA to fal.ai: {e}")

        endpoint = "fal-ai/flux-lora" if lora_url else f"fal-ai/{model}"

        payload: dict[str, Any] = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
        }
        if lora_url:
            payload["loras"] = [{"path": lora_url, "scale": lora_scale}]
        if inputs.get("seed") is not None:
            payload["seed"] = inputs["seed"]
        if inputs.get("num_inference_steps"):
            payload["num_inference_steps"] = inputs["num_inference_steps"]
        if inputs.get("guidance_scale"):
            payload["guidance_scale"] = inputs["guidance_scale"]
        if inputs.get("negative_prompt"):
            payload["negative_prompt"] = inputs["negative_prompt"]

        try:
            response = requests.post(
                f"https://fal.run/{endpoint}",
                headers={
                    "Authorization": f"Key {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()

            image_url = data["images"][0]["url"]
            image_response = requests.get(image_url, timeout=60)
            image_response.raise_for_status()

            output_path = Path(inputs.get("output_path", "generated_image.png"))
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # fal.ai's flux-pro endpoints return JPEG bytes regardless of the
            # requested output filename's extension. Writing those bytes under
            # a mismatched extension (e.g. .png) produces a file that image
            # decoders (browsers, Remotion/Chromium) refuse to load, since the
            # magic bytes don't match the extension's expected format. Sniff
            # the real format from the content-type header (falling back to
            # magic-byte detection) and correct the extension before writing.
            actual_ext = None
            content_type = image_response.headers.get("content-type", "")
            if "jpeg" in content_type or "jpg" in content_type:
                actual_ext = ".jpg"
            elif "png" in content_type:
                actual_ext = ".png"
            elif "webp" in content_type:
                actual_ext = ".webp"
            elif image_response.content[:2] == b"\xff\xd8":
                actual_ext = ".jpg"
            elif image_response.content[:8] == b"\x89PNG\r\n\x1a\n":
                actual_ext = ".png"

            if actual_ext and output_path.suffix.lower() != actual_ext:
                output_path = output_path.with_suffix(actual_ext)

            output_path.write_bytes(image_response.content)

        except Exception as e:
            return ToolResult(success=False, error=f"FLUX generation failed: {e}")

        return ToolResult(
            success=True,
            data={
                "provider": "flux",
                "model": endpoint,
                "prompt": prompt,
                "output": str(output_path),
                "seed": data.get("seed"),
                "lora_url": lora_url,
                "lora_scale": lora_scale if lora_url else None,
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            seed=data.get("seed"),
            model=f"fal-ai/{endpoint}" if not endpoint.startswith("fal-ai/") else endpoint,
        )
