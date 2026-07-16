"""Sarvam AI text-to-speech provider tool — Indic-language narration (bulbul:v3)."""

from __future__ import annotations

import base64
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


class SarvamTTS(BaseTool):
    name = "sarvam_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "sarvam"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API

    dependencies = ["pip:requests"]
    install_instructions = (
        "Set SARVAM_API_KEY to your Sarvam AI API subscription key.\n"
        "  Get one at https://dashboard.sarvam.ai/\n"
        "Sarvam specializes in Indic-language TTS/STT (Hindi and 10+ other "
        "Indian languages) via the bulbul voice model."
    )
    fallback = "edge_tts"
    fallback_tools = ["edge_tts", "google_tts", "elevenlabs_tts"]
    agent_skills = ["text-to-speech"]

    capabilities = [
        "text_to_speech",
        "voice_selection",
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
        "Hindi and other Indic-language narration with natural-sounding native speakers",
        "Indian-accented delivery that generic multilingual TTS providers render less naturally",
    ]
    not_good_for = [
        "non-Indic languages",
        "voice cloning",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to convert to speech (max 2500 chars for bulbul:v3)",
            },
            "target_language_code": {
                "type": "string",
                "default": "hi-IN",
                "description": "BCP-47 language code, e.g. hi-IN, ta-IN, bn-IN",
            },
            "speaker": {
                "type": "string",
                "default": "roopa",
                "description": (
                    "bulbul:v3 speaker name (lowercase). Female-leaning: roopa, priya, ritu, neha, "
                    "pooja, simran, kavya, ishita, shreya, tanya, shruti, suhani, kavitha, "
                    "rupali. Male-leaning: shubh (default per Sarvam), aditya, rahul, rohan, "
                    "amit, dev, kabir, varun, and others."
                ),
            },
            "model": {
                "type": "string",
                "default": "bulbul:v3",
                "enum": ["bulbul:v3", "bulbul:v2"],
            },
            "pace": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.5,
                "maximum": 2.0,
                "description": "Speaking pace. 1.0 = normal. bulbul:v2 supports 0.3-3.0.",
            },
            "pitch": {
                "type": "number",
                "default": 0.0,
                "minimum": -0.75,
                "maximum": 0.75,
                "description": "Pitch adjustment. bulbul:v2 only (ignored on v3).",
            },
            "temperature": {
                "type": "number",
                "default": 0.6,
                "minimum": 0.01,
                "maximum": 2.0,
                "description": "bulbul:v3 only — higher values add more delivery variation.",
            },
            "speech_sample_rate": {
                "type": "string",
                "default": "24000",
                "enum": ["8000", "16000", "22050", "24000", "32000", "44100", "48000"],
            },
            "output_audio_codec": {
                "type": "string",
                "default": "wav",
                "enum": ["mp3", "linear16", "mulaw", "alaw", "opus", "flac", "aac", "wav"],
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=10, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = [
        "text",
        "target_language_code",
        "speaker",
        "model",
        "pace",
        "pitch",
        "temperature",
    ]
    side_effects = ["writes audio file to output_path", "calls the Sarvam AI TTS API"]
    user_visible_verification = ["Listen to generated audio for natural Hindi pronunciation and delivery"]

    _EXT_MAP = {
        "mp3": "mp3",
        "wav": "wav",
        "linear16": "wav",
        "mulaw": "wav",
        "alaw": "wav",
        "opus": "opus",
        "flac": "flac",
        "aac": "aac",
    }

    def _get_api_key(self) -> str | None:
        return os.environ.get("SARVAM_API_KEY")

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        # Approximate — Sarvam does not publish a fixed public per-character
        # rate at time of writing; this mirrors typical Indic-TTS API pricing
        # (~$15 per 1M characters) as a conservative planning estimate.
        text = inputs.get("text", "")
        return round(len(text) * 0.000015, 5)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="No SARVAM_API_KEY found. " + self.install_instructions,
            )

        start = time.time()
        try:
            result = self._generate(inputs, api_key=api_key)
        except Exception as exc:
            return ToolResult(success=False, error=f"Sarvam TTS generation failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        if result.success:
            result.cost_usd = self.estimate_cost(inputs)
        return result

    def _generate(self, inputs: dict[str, Any], api_key: str) -> ToolResult:
        import requests

        text = inputs["text"]
        target_language_code = inputs.get("target_language_code", "hi-IN")
        speaker = inputs.get("speaker", "priya")
        model = inputs.get("model", "bulbul:v3")
        pace = inputs.get("pace", 1.0)
        speech_sample_rate = str(inputs.get("speech_sample_rate", "24000"))
        output_audio_codec = inputs.get("output_audio_codec", "wav")

        payload: dict[str, Any] = {
            "text": text,
            "target_language_code": target_language_code,
            "speaker": speaker,
            "model": model,
            "pace": pace,
            "speech_sample_rate": speech_sample_rate,
            "output_audio_codec": output_audio_codec,
        }
        if model == "bulbul:v2":
            payload["pitch"] = inputs.get("pitch", 0.0)
        else:
            payload["temperature"] = inputs.get("temperature", 0.6)

        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json",
        }

        response = requests.post(
            "https://api.sarvam.ai/text-to-speech",
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        body = response.json()

        audios = body.get("audios") or []
        if not audios:
            return ToolResult(success=False, error=f"Sarvam TTS returned no audio: {body}")

        audio_bytes = base64.b64decode(audios[0])

        ext = self._EXT_MAP.get(output_audio_codec, "wav")
        output_path = Path(inputs.get("output_path", f"tts_output.{ext}"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)

        return ToolResult(
            success=True,
            data={
                "provider": "sarvam",
                "voice": speaker,
                "target_language_code": target_language_code,
                "text_length": len(text),
                "output": str(output_path),
                "format": output_audio_codec,
                "request_id": body.get("request_id"),
            },
            artifacts=[str(output_path)],
            model=f"sarvam/{model}/{speaker}",
        )
