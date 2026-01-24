from __future__ import annotations

import os
import wave
from pathlib import Path

from piper.voice import PiperVoice

from app.tts.espeak_setup import ensure_espeak_data_env


_voice: PiperVoice | None = None


def _default_voice_paths() -> tuple[str, str] | None:
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"

    model = data_dir / "en_US-lessac-medium.onnx"
    config = data_dir / "en_US-lessac-medium.onnx.json"

    if model.exists() and config.exists():
        return str(model), str(config)

    return None


def _get_voice() -> PiperVoice:
    global _voice
    if _voice is not None:
        return _voice

    # Ensure ESPEAK_DATA_PATH is set if we can auto-detect it.
    ensure_espeak_data_env()

    model_path = os.getenv("PIPER_VOICE_MODEL_PATH")
    config_path = os.getenv("PIPER_VOICE_CONFIG_PATH")

    if not model_path or not config_path:
        defaults = _default_voice_paths()
        if defaults:
            model_path, config_path = defaults

    if not model_path or not config_path:
        raise RuntimeError(
            "Missing Piper voice configuration. Either set env vars PIPER_VOICE_MODEL_PATH and PIPER_VOICE_CONFIG_PATH, "
            "or place en_US-lessac-medium.onnx and en_US-lessac-medium.onnx.json in backend/app/data/."
        )

    _voice = PiperVoice.load(model_path, config_path)
    return _voice


def synthesize_speech_wav(text: str) -> bytes:
    """Synthesize speech using Piper and return WAV bytes."""

    voice = _get_voice()

    # Piper returns (samples, sample_rate)
    samples, sample_rate = voice.synthesize(text)
    if not samples:
        return b""

    import io

    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sample_rate))
        wf.writeframes(bytes(samples))

    return wav_io.getvalue()
