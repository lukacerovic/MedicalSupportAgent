from __future__ import annotations

import io
import os

from pydub import AudioSegment
from piper.voice import PiperVoice


# Cache the voice so we don't reload it on every request.
_voice: PiperVoice | None = None


def _get_voice() -> PiperVoice:
    global _voice
    if _voice is not None:
        return _voice

    # Configure via env vars so this works in different environments.
    # Example:
    #   export PIPER_VOICE_MODEL_PATH=backend/app/data/en_US-lessac-medium.onnx
    #   export PIPER_VOICE_CONFIG_PATH=backend/app/data/en_US-lessac-medium.onnx.json
    model_path = os.getenv("PIPER_VOICE_MODEL_PATH")
    config_path = os.getenv("PIPER_VOICE_CONFIG_PATH")

    if not model_path or not config_path:
        raise RuntimeError(
            "Missing Piper voice configuration. Set env vars PIPER_VOICE_MODEL_PATH and PIPER_VOICE_CONFIG_PATH."
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
