from __future__ import annotations

import os
import ssl

import anyio
import certifi


def synthesize_speech_mp3(text: str) -> bytes:
    """Synthesize speech using edge-tts and return MP3 bytes.

    Windows note:
    Some machines have broken/malformed certificates in the Windows certificate
    store which causes `ssl.create_default_context()` to raise:
      - "cadata does not contain a certificate"
      - "[ASN1] nested asn1 error"

    edge-tts depends on aiohttp, which creates a default SSL context by default.
    We work around this by preconfiguring aiohttp to use an explicit SSL context
    built from certifi's CA bundle.

    If that still fails, we fall back to disabling SSL verification (last resort)
    so the app remains usable.
    """

    voice = os.getenv("EDGE_TTS_VOICE", "en-US-JennyNeural")
    rate = os.getenv("EDGE_TTS_RATE", "+0%")
    volume = os.getenv("EDGE_TTS_VOLUME", "+0%")

    async def _run() -> bytes:
        # Import inside the coroutine so any monkey-patching happens before use.
        import aiohttp
        import edge_tts

        # 1) Preferred: explicit CA bundle from certifi
        try:
            cafile = certifi.where()
            ssl_ctx = ssl.create_default_context(cafile=cafile)
            connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        except Exception as e:
            # 2) Last resort: disable SSL verification entirely
            # WARNING: This reduces security (MITM possible).
            connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(connector=connector) as session:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume,
                session=session,
            )

            out = bytearray()
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    out.extend(chunk["data"])

            return bytes(out)

    return anyio.run(_run)
