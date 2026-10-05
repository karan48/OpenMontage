"""Reference-conditioned image generation on fal.ai (Meta Muse edit, FLUX Kontext).

Draws a known character in a new scene from approved reference images: the
fix for the face drift and two-shot wardrobe swaps that text-only prompts
can't prevent. Prompts and ordered reference lists normally come from
lib/character_bible.py (build_shot / build_ref_job / build_variant).
"""

from __future__ import annotations

import base64
import io
import mimetypes
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

# Per-model limits and list prices (fal get_pricing, 2026-10-04). Check the
# live price before a batch: fal changes prices without notice.
MODELS: dict[str, dict[str, Any]] = {
    "meta/muse-image/edit": {"min_refs": 1, "max_refs": 10, "usd_per_image": 0.01, "seed": False},
    "fal-ai/flux-pro/kontext": {"min_refs": 1, "max_refs": 1, "usd_per_image": 0.04, "seed": True},
}
DEFAULT_MODEL = "meta/muse-image/edit"

# References larger than this are re-encoded before upload; data URIs of
# 3 MB PNGs make slow, fragile requests and add nothing to identity.
MAX_REF_SIDE = 1536
MAX_REF_BYTES = 2_000_000


def _image_to_data_uri(path: str) -> str:
    source = Path(path)
    raw = source.read_bytes()
    mime = mimetypes.guess_type(source.name)[0] or "image/jpeg"

    from PIL import Image

    with Image.open(io.BytesIO(raw)) as image:
        too_big = len(raw) > MAX_REF_BYTES or max(image.size) > MAX_REF_SIDE
        if too_big:
            if image.mode in ("RGBA", "LA", "P"):
                rgba = image.convert("RGBA")
                flat = Image.new("RGB", rgba.size, (255, 255, 255))
                flat.paste(rgba, mask=rgba.split()[-1])
                image = flat
            else:
                image = image.convert("RGB")
            image.thumbnail((MAX_REF_SIDE, MAX_REF_SIDE))
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=92)
            raw, mime = buffer.getvalue(), "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


class FalReferenceImage(BaseTool):
    name = "fal_reference_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "fal"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []  # FAL_KEY (or FAL_AI_API_KEY), checked in get_status
    install_instructions = (
        "Set FAL_KEY to your fal.ai API key.\n"
        "  Get one at https://fal.ai/dashboard/keys"
    )
    agent_skills = ["reference-image-edit", "flux-best-practices"]

    capabilities = ["image_edit", "image_to_image", "reference_image_generation"]
    supports = {
        "image_edit": True,
        "reference_image": True,
        "multiple_reference_images": True,
        "requires_reference_image": True,
        "custom_aspect_ratio": True,
        "seed": False,
    }
    best_for = [
        "the same recurring character in a new scene, from approved reference images",
        "pose, expression and outfit references drawn from a character's approved master",
        "change-one-thing variants of an approved still (blink, tear, mouth open)",
        "two-shots of two known characters without swapped faces or clothes",
        "cheap: about $0.01 per image with Meta Muse edit",
    ]
    not_good_for = [
        "text-only generation: it needs at least one reference image",
        "exact lettering or signage",
        "reproducible output: Muse takes no seed, so keep every image you may want again",
    ]

    input_schema = {
        "type": "object",
        "required": ["prompt", "output_path"],
        "properties": {
            "prompt": {"type": "string"},
            "image_path": {"type": "string", "description": "Single local reference image (becomes image 1)."},
            "image_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Local reference images in prompt order (image 1, image 2, …). Sent as data URIs.",
            },
            "image_url": {"type": "string", "description": "Single hosted reference image."},
            "image_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Hosted reference images, numbered after the local ones.",
            },
            "model": {
                "type": "string",
                "enum": list(MODELS),
                "default": DEFAULT_MODEL,
                "description": "meta/muse-image/edit: 1-10 references, no seed. fal-ai/flux-pro/kontext: exactly 1 reference, seeded.",
            },
            "model_name": {"type": "string", "description": "Alias of model (image_selector vocabulary)."},
            "aspect_ratio": {"type": "string", "description": "W:H, e.g. 16:9 or 9:16."},
            "num_images": {"type": "integer", "minimum": 1, "maximum": 4, "default": 1},
            "output_format": {"type": "string", "enum": ["jpeg", "png", "webp"], "default": "jpeg"},
            "seed": {"type": "integer", "description": "Kontext only; Muse has no seed."},
            "guidance_scale": {"type": "number", "default": 3.5, "description": "Kontext only."},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=50, network_required=True)
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "image_path", "image_paths", "image_url", "image_urls", "model", "aspect_ratio", "seed"]
    side_effects = ["writes image file(s) to output_path", "paid call to fal.ai"]
    user_visible_verification = [
        "Compare each character against their approved master reference: face, hair, skin tone, outfit, accessories",
        "Check for AI lettering, watermarks and swapped clothes in two-shots",
    ]

    @staticmethod
    def _api_key() -> str | None:
        return os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY")

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE if self._api_key() else ToolStatus.UNAVAILABLE

    @staticmethod
    def _model(inputs: dict[str, Any]) -> str:
        return inputs.get("model") or inputs.get("model_name") or DEFAULT_MODEL

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        spec = MODELS.get(self._model(inputs), MODELS[DEFAULT_MODEL])
        return round(spec["usd_per_image"] * int(inputs.get("num_images") or 1), 4)

    @staticmethod
    def _references(inputs: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Return (payload references, labels) in prompt order: local paths first, then URLs."""
        locals_ = ([inputs["image_path"]] if inputs.get("image_path") else []) + list(inputs.get("image_paths") or [])
        hosted = ([inputs["image_url"]] if inputs.get("image_url") else []) + list(inputs.get("image_urls") or [])
        for path in locals_:
            if not Path(path).exists():
                raise FileNotFoundError(f"reference image not found: {path}")
        payload = [_image_to_data_uri(p) for p in locals_] + hosted
        return payload, [str(p) for p in locals_] + hosted

    def _payload(self, model: str, inputs: dict[str, Any], refs: list[str]) -> dict[str, Any]:
        output_format = inputs.get("output_format") or "jpeg"
        payload: dict[str, Any] = {"prompt": inputs["prompt"], "num_images": int(inputs.get("num_images") or 1)}
        if inputs.get("aspect_ratio"):
            payload["aspect_ratio"] = inputs["aspect_ratio"]
        if model == "fal-ai/flux-pro/kontext":
            payload["image_url"] = refs[0]
            payload["guidance_scale"] = float(inputs.get("guidance_scale", 3.5))
            payload["output_format"] = "png" if output_format == "png" else "jpeg"
            if inputs.get("seed") is not None:
                payload["seed"] = int(inputs["seed"])
        else:
            payload["image_urls"] = refs
            payload["output_format"] = output_format
        return payload

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._api_key()
        if not api_key:
            return ToolResult(success=False, error="FAL_KEY not set. " + self.install_instructions)
        if not (inputs.get("prompt") or "").strip():
            return ToolResult(success=False, error="prompt is required")
        if not inputs.get("output_path"):
            return ToolResult(success=False, error="output_path is required (write under projects/<project-id>/)")

        model = self._model(inputs)
        if model not in MODELS:
            return ToolResult(success=False, error=f"unknown model '{model}' (use one of {', '.join(MODELS)})")
        spec = MODELS[model]

        try:
            refs, labels = self._references(inputs)
        except (FileNotFoundError, OSError) as exc:
            return ToolResult(success=False, error=str(exc))
        if not spec["min_refs"] <= len(refs) <= spec["max_refs"]:
            return ToolResult(
                success=False,
                error=(
                    f"{model} takes {spec['min_refs']}-{spec['max_refs']} reference image(s); got {len(refs)}. "
                    "Use flux_image for text-only generation."
                ),
            )

        import requests

        start = time.time()
        try:
            response = requests.post(
                f"https://fal.run/{model}",
                headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
                json=self._payload(model, inputs, refs),
                timeout=300,
            )
        except requests.RequestException as exc:
            return ToolResult(success=False, error=_explain_dropped_request(model, api_key, exc))

        if response.status_code in (401, 403):
            return ToolResult(success=False, error=_key_rejected(model, response.status_code, response.text))
        if response.status_code == 422 and "content_policy" in response.text:
            return ToolResult(
                success=False,
                error=(
                    "content_policy_violation: fal refused the prompt or a reference image (not billed). "
                    f"Rephrase the scene neutrally and retry once. Detail: {response.text[:300]}"
                ),
            )
        if response.status_code >= 400:
            return ToolResult(success=False, error=f"fal HTTP {response.status_code}: {response.text[:400]}")

        data = response.json()
        images = data.get("images") or []
        if not images:
            return ToolResult(success=False, error=f"fal returned no images: {str(data)[:300]}")

        output_path = Path(inputs["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        try:
            for index, image in enumerate(images):
                download = requests.get(image["url"], timeout=120)
                download.raise_for_status()
                target = output_path if len(images) == 1 else output_path.with_name(
                    f"{output_path.stem}_{index + 1}{output_path.suffix}"
                )
                target = target.with_suffix(_sniff_extension(download, target.suffix))
                target.write_bytes(download.content)
                written.append(str(target))
        except Exception as exc:  # noqa: BLE001 — surface any download failure as a tool error
            return ToolResult(success=False, error=f"downloading fal output failed: {exc}", artifacts=written)

        cost = round(spec["usd_per_image"] * len(written), 4)
        return ToolResult(
            success=True,
            data={
                "provider": "fal",
                "model": model,
                "prompt": inputs["prompt"],
                "output": written[0],
                "outputs": written,
                "references": labels,
                "reference_count": len(labels),
                "aspect_ratio": inputs.get("aspect_ratio"),
                "seed": data.get("seed"),
            },
            artifacts=written,
            cost_usd=cost,
            duration_seconds=round(time.time() - start, 2),
            seed=data.get("seed"),
            model=model,
        )


def _key_rejected(model: str, status: int, body: str) -> str:
    return (
        f"fal rejected this API key for {model} (HTTP {status}: {body[:80]!r}); not billed. "
        "The key may belong to another fal account or lack access to this model. Check it in the fal "
        "dashboard, or create a key on the account that can run the model, and update FAL_KEY in .env."
    )


def _explain_dropped_request(model: str, api_key: str, exc: Exception) -> str:
    """Tell a network failure from an auth rejection hidden behind it.

    fal answers 401/403 as soon as it reads the headers and closes the socket,
    so a large request body dies mid-upload with an SSL/connection error
    instead of the real status. A tiny probe with an empty body (invalid
    input: never runs, never billed) shows which it was.
    """
    import requests

    try:
        probe = requests.post(
            f"https://fal.run/{model}",
            headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
            json={},
            timeout=30,
        )
    except requests.RequestException:
        return f"fal request failed (network): {exc}"
    if probe.status_code in (401, 403):
        return _key_rejected(model, probe.status_code, probe.text)
    return f"fal request failed: {exc}"


def _sniff_extension(response: Any, fallback: str) -> str:
    content_type = response.headers.get("content-type", "") if hasattr(response, "headers") else ""
    content = response.content[:12]
    if "jpeg" in content_type or "jpg" in content_type or content[:2] == b"\xff\xd8":
        return ".jpg"
    if "png" in content_type or content[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if "webp" in content_type or (content[:4] == b"RIFF" and content[8:12] == b"WEBP"):
        return ".webp"
    return fallback or ".jpg"
