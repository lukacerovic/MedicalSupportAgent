from __future__ import annotations

import os

import anyio
import certifi
import edge_tts


def synthesize_speech_mp3(text: str) -> bytes:
    """Synthesize speech using edge-tts and return MP3 bytes.

    NOTE (Windows): Some environments have malformed certificates in the Windows
    certificate store, which can make Python's ssl.create_default_context() fail
    with: "cadata does not contain a certificate".

    We force aiohttp (used by edge-tts) to use certifi's CA bundle instead.
    """

    # Make aiohttp/ssl use certifi bundle instead of Windows cert store
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())

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
