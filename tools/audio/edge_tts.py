"""Microsoft Edge neural text-to-speech provider tool (free, no API key)."""

from __future__ import annotations

import asyncio
import shutil
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


class EdgeTTS(BaseTool):
    name = "edge_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "edge_tts"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API

    dependencies = ["pip:edge-tts"]
    install_instructions = (
        "Install the edge-tts package:\n"
        "  pip install edge-tts\n"
        "No API key needed — uses Microsoft Edge's free neural voice service. "
        "This is an unofficial/reverse-engineered endpoint (not a supported "
        "paid Azure API), so treat it as a free-tier convenience option, not "
        "a guaranteed-uptime production dependency."
    )
    agent_skills = ["text-to-speech"]

    capabilities = [
        "text_to_speech",
        "multilingual_generation",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": False,
        "native_audio": True,
        "ssml": False,
    }
    best_for = [
        "free, natural-sounding multilingual narration (700+ neural voices)",
        "quick free alternative when paid TTS providers are unavailable",
    ]
    not_good_for = [
        "guaranteed uptime / officially supported production use",
        "voice cloning",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "voice": {
                "type": "string",
                "default": "en-US-AriaNeural",
                "description": "Edge neural voice name, e.g. hi-IN-MadhurNeural (male), hi-IN-SwaraNeural (female)",
            },
            "rate": {
                "type": "string",
                "default": "+0%",
                "description": "Speaking rate adjustment, e.g. '+10%', '-15%'",
            },
            "pitch": {
                "type": "string",
                "default": "+0Hz",
                "description": "Pitch adjustment, e.g. '+20Hz', '-10Hz'",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=10, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["timeout", "connection"])
    idempotency_key_fields = ["text", "voice", "rate", "pitch"]
    side_effects = ["writes audio file to output_path", "network call to Microsoft Edge TTS service"]
    user_visible_verification = ["Listen to generated audio for intelligibility and naturalness"]

    def get_status(self) -> ToolStatus:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return ToolStatus.UNAVAILABLE
        return ToolStatus.AVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(success=False, error="edge-tts not available. " + self.install_instructions)

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Edge TTS generation failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        return result

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        import edge_tts

        output_path = Path(inputs.get("output_path", "tts_output.mp3"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice = inputs.get("voice", "en-US-AriaNeural")
        rate = inputs.get("rate", "+0%")
        pitch = inputs.get("pitch", "+0Hz")
        text = inputs["text"]

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(str(output_path))

        asyncio.run(_run())

        if not output_path.exists():
            return ToolResult(success=False, error=f"Edge TTS output file missing: {output_path}")

        return ToolResult(
            success=True,
            data={
                "provider": "edge_tts",
                "voice": voice,
                "text_length": len(text),
                "output": str(output_path),
                "format": output_path.suffix.lstrip("."),
            },
        )
