from __future__ import annotations

import os

import anyio
import edge_tts


def synthesize_speech_mp3(text: str) -> bytes:
    """Synthesize speech using edge-tts and return MP3 bytes.

    edge-tts is free to use and does not require API keys.
    It uses Microsoft Edge's online neural voices.
    """

    voice = os.getenv("EDGE_TTS_VOICE", "en-US-JennyNeural")
    rate = os.getenv("EDGE_TTS_RATE", "+0%")
    volume = os.getenv("EDGE_TTS_VOLUME", "+0%")

    async def _run() -> bytes:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
        out = bytearray()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                out.extend(chunk["data"])
        return bytes(out)

    return anyio.run(_run)
