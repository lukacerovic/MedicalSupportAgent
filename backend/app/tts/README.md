# Backend TTS

This backend returns **audio/mpeg** (MP3) from `/start_session` and `/message`.

## Configure Piper voice

Set these env vars before starting the backend:

- `PIPER_VOICE_MODEL_PATH` (path to `.onnx` model)
- `PIPER_VOICE_CONFIG_PATH` (path to `.onnx.json` config)

Example:

```bash
export PIPER_VOICE_MODEL_PATH=backend/app/data/en_US-lessac-medium.onnx
export PIPER_VOICE_CONFIG_PATH=backend/app/data/en_US-lessac-medium.onnx.json
```

## Notes

- The session id is returned in the `X-Session-Id` response header from `/start_session`.
- Frontend plays audio and only resumes listening after playback ends.
