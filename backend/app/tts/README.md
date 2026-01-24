# Backend TTS

This backend returns an audio response from `/message`.

## Option A (recommended on Windows): edge-tts

Install:

```bash
pip install edge-tts
```

It uses Microsoft Edge's online TTS voices (no API key). Default voice is `en-US-JennyNeural`.

Optional env vars:

- `EDGE_TTS_VOICE` (e.g. `en-US-JennyNeural`)
- `EDGE_TTS_RATE` (e.g. `+0%`, `-10%`, `+10%`)
- `EDGE_TTS_VOLUME` (e.g. `+0%`, `+20%`)

## Option B: Piper (offline)

Piper requires extra setup on Windows (eSpeak NG data). If you still want Piper, use the `piper_*` modules in this folder.
