from __future__ import annotations

import io
import os
from pathlib import Path

from pydub import AudioSegment
from piper.voice import PiperVoice


# Cache the voice so we don't reload it on every request.
_voice: PiperVoice | None = None


def _default_voice_paths() -> tuple[str, str] | None:
    """Return default model/config paths if they exist inside the repo.

    This makes local dev on Windows easy: you can just drop the files into
    backend/app/data/ and run without setting env vars.
    """

    # This file lives at backend/app/tts/piper_tts.py
    # So backend/app/data is: ../../data
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

    # Configure via env vars so this works in different environments.
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


def synthesize_speech_mp3(text: str) -> bytes:
    """Synthesize speech using Piper and return MP3 bytes."""
    voice = _get_voice()

    wav_io = io.BytesIO()
    # Piper writes 16-bit PCM WAV.
    voice.synthesize(text, wav_io)
    wav_io.seek(0)

    audio = AudioSegment.from_file(wav_io, format="wav")
    mp3_io = io.BytesIO()
    audio.export(mp3_io, format="mp3")
    return mp3_io.getvalue()
