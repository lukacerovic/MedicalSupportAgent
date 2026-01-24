from __future__ import annotations

import os

import anyio


def synthesize_speech_mp3(text: str) -> bytes:
    """Synthesize speech using edge-tts and return MP3 bytes.

    IMPORTANT (Windows):
    Your Python/Windows certificate store is broken such that importing aiohttp
    crashes because aiohttp creates default SSL contexts at import time.

    Therefore we avoid aiohttp entirely and use edge-tts as a CLI tool.
    This keeps the project free and avoids SSL store issues.

    Requires:
      pip install edge-tts

    This returns MP3 bytes written by edge-tts.
    """

    voice = os.getenv("EDGE_TTS_VOICE", "en-US-JennyNeural")
    rate = os.getenv("EDGE_TTS_RATE", "+0%")
    volume = os.getenv("EDGE_TTS_VOLUME", "+0%")

    async def _run() -> bytes:
        import tempfile
        import subprocess

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        try:
            # Use stdin to pass text to avoid quoting issues on Windows.
            cmd = [
                "edge-tts",
                "--voice",
                voice,
                "--rate",
                rate,
                "--volume",
                volume,
                "--write-media",
                out_path,
                "--text",
                text,
            ]

            # Run in a worker thread to not block the event loop.
            def _run_proc():
                subprocess.run(cmd, check=True, capture_output=True)

            await anyio.to_thread.run_sync(_run_proc)

            with open(out_path, "rb") as rf:
                return rf.read()
        finally:
            try:
                os.remove(out_path)
            except Exception:
                pass

    return anyio.run(_run)
