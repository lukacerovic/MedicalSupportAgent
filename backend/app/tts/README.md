# Backend TTS

## Current mode: Piper (offline)

`POST /message` returns `audio/wav` generated on the backend.

### Requirements

1) Install **eSpeak NG** on Windows (needed for phonemization). Piper will fail if it can't find `phontab` inside `espeak-ng-data`.

2) Place voice files in:

- `backend/app/data/en_US-lessac-medium.onnx`
- `backend/app/data/en_US-lessac-medium.onnx.json`

### Optional env vars

- `PIPER_VOICE_MODEL_PATH`
- `PIPER_VOICE_CONFIG_PATH`
- `ESPEAK_DATA_PATH` (path to folder containing `phontab`, e.g. `C:\Program Files\eSpeak NG\espeak-ng-data`)

The backend tries to auto-detect `ESPEAK_DATA_PATH` from common Windows install locations.
