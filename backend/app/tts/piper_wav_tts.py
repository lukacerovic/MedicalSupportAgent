from __future__ import annotations

import os
import io
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
    """Synthesize speech using Piper and return WAV bytes (with header)."""
    voice = _get_voice()

    # Preferred path for your Piper version: synthesize_wav(text, wav_file)
    if hasattr(voice, "synthesize_wav"):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        return buf.getvalue()

    # Fallback: try synthesize() iterator of bytes (best-effort)
    out = bytearray()
    synth = voice.synthesize(text)
    try:
        for chunk in synth:
            if isinstance(chunk, (bytes, bytearray)):
                out.extend(chunk)
    except TypeError:
        return b""

    return bytes(out)


def get_wav_header() -> bytes:
    """Return a standard WAV header for streaming (16-bit mono 22050Hz usually)."""
    # Piper defaults: 22050Hz, 1 channel, 16-bit usually. 
    # We create a dummy header.
    voice = _get_voice()
    sample_rate = voice.config.sample_rate
    
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(sample_rate)
        # Write 0 frames to get just the header
        pass
    
    # wave.open writes header only when closed or data written. 
    # But it might need to know length. 
    # For streaming, we often set length to something huge or ignore.
    # Standard WAV header is 44 bytes.
    # Let's generate a header with "unknown" length (common in streaming).
    # Easier: generate a tiny wav and take the first 44 bytes.
    return synthesize_speech_wav("a")[:44]


def synthesize_speech_raw(text: str) -> bytes:
    """Synthesize speech and return raw PCM bytes (no header)."""
    wav_data = synthesize_speech_wav(text)
    if len(wav_data) > 44:
        return wav_data[44:] # Skip 44-byte header
    return b""
