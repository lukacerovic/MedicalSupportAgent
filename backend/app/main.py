from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.agent.base_agent import BaseAgent
from app.memory.session_memory import memory

import os
import time
import uuid
import subprocess
from pathlib import Path

# Load your AI agent
agent = BaseAgent(system_prompt="You are Ana, a medical support agent for BelMedic. Answer user questions about services and reservations politely and informatively.")

app = FastAPI()

# ---- audio output directory (served as static) ----
AUDIO_DIR = Path("app/static/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class MessageRequest(BaseModel):
    session_id: str
    user_message: str

# Start new session
@app.get("/start_session")
def start_session():
    session_id = str(uuid.uuid4())
    memory.init(session_id)
    return {"session_id": session_id, "greeting": "Hello, this is Ana from BelMedic. How can I help you today?"}


def _tts_to_wav(text: str, wav_path: Path) -> None:
    """Generate a WAV file from text using Piper CLI.

    Assumes `piper` is available on PATH and a model exists at `app/data/voice.onnx`.
    """
    model_path = Path("app/data/voice.onnx")
    if not model_path.exists():
        raise FileNotFoundError(
            "Missing Piper model at app/data/voice.onnx. Add a Piper .onnx model (and optionally .json config) before using TTS."
        )

    # Piper CLI example uses stdin for text and `--output_file` for WAV output.
    # See Piper CLI docs/examples for --model / --output_file usage.
    cmd = ["piper", "--model", str(model_path), "--output_file", str(wav_path)]
    subprocess.run(cmd, input=text.encode("utf-8"), check=True)


# Existing: Send user message to agent and get response (text)
@app.post("/message")
def message(req: MessageRequest):
    t0 = time.perf_counter()

    memory.add_user(req.session_id, req.user_message)

    t_llm0 = time.perf_counter()
    ai_response = agent.respond(memory.get(req.session_id))
    t_llm1 = time.perf_counter()

    memory.add_ai(req.session_id, ai_response)

    convo = memory.get(req.session_id)
    print("\n--- Conversation Dump ---")
    for idx, msg in enumerate(convo):
        role = "user" if idx % 2 == 0 else "assistant"
        print(f"[{idx:02d}] {role}: {msg}")
    print(f"LLM time: {(t_llm1 - t_llm0):.3f}s")
    print(f"Total time: {(time.perf_counter() - t0):.3f}s")
    print("--- End Conversation Dump ---\n")

    return {"response": ai_response}


# New: Two-step endpoint that returns text + URL to audio
@app.post("/message_tts")
def message_tts(req: MessageRequest):
    t0 = time.perf_counter()

    memory.add_user(req.session_id, req.user_message)

    t_llm0 = time.perf_counter()
    ai_response = agent.respond(memory.get(req.session_id))
    t_llm1 = time.perf_counter()

    memory.add_ai(req.session_id, ai_response)

    # create deterministic-ish filename
    audio_id = str(uuid.uuid4())
    wav_filename = f"{req.session_id}_{audio_id}.wav"
    wav_path = AUDIO_DIR / wav_filename

    t_tts0 = time.perf_counter()
    _tts_to_wav(ai_response, wav_path)
    t_tts1 = time.perf_counter()

    convo = memory.get(req.session_id)
    print("\n--- Conversation Dump (TTS) ---")
    for idx, msg in enumerate(convo):
        role = "user" if idx % 2 == 0 else "assistant"
        print(f"[{idx:02d}] {role}: {msg}")
    print(f"LLM time: {(t_llm1 - t_llm0):.3f}s")
    print(f"TTS time: {(t_tts1 - t_tts0):.3f}s")
    print(f"Total time: {(time.perf_counter() - t0):.3f}s")
    print("--- End Conversation Dump (TTS) ---\n")

    # audio will be downloadable via /static/audio/<filename>
    return {
        "response_text": ai_response,
        "audio_url": f"/static/audio/{wav_filename}",
    }
