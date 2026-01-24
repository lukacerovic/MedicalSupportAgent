from __future__ import annotations

import os
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
    """Synthesize speech using Piper and return WAV bytes.

    Piper's Python API differs across versions.

    Some versions expose PiperVoice.synthesize_wav(text, wav_file) where wav_file
    is a file-like object opened in binary mode.

    We support that signature by writing to an in-memory BytesIO.
    """

    voice = _get_voice()

    import io

    # Try synthesize_wav(text, wav_file)
    if hasattr(voice, "synthesize_wav"):
        wav_io = io.BytesIO()
        try:
            voice.synthesize_wav(text, wav_io)
            return wav_io.getvalue()
        except TypeError:
            # Different signature; fall through.
            pass

    # Fallback: try synthesize() iterator of bytes
    out = bytearray()
    synth = voice.synthesize(text)
    try:
        for chunk in synth:
            if isinstance(chunk, (bytes, bytearray)):
                out.extend(chunk)
    except TypeError:
        return b""

    return bytes(out)
