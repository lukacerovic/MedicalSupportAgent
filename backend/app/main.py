from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from app.agent.base_agent import BaseAgent
from app.memory.session_memory import memory

import time
import uuid
import subprocess
from pathlib import Path

# More concise, call-assistant style prompt
SYSTEM_PROMPT = (
    "You are Ana, BelMedic call assistant. "
    "Be brief and practical. "
    "Ask one clear question at a time when you need missing details. "
    "Do not add extra info unless asked. "
    "If the user asks about services or reservations, help them complete it."
)

agent = BaseAgent(system_prompt=SYSTEM_PROMPT)

app = FastAPI()

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageRequest(BaseModel):
    session_id: str
    user_message: str

@app.get("/start_session")
def start_session():
    session_id = str(uuid.uuid4())
    memory.init(session_id)
    return {"session_id": session_id, "greeting": "BelMedic. Ana speaking. How can I help?"}


def _tts_to_wav_bytes(text: str) -> bytes:
    """Generate WAV audio bytes from text using Piper CLI.

    Assumes `piper` is available on PATH and a model exists at `app/data/voice.onnx`.
    """
    model_path = Path("app/data/voice.onnx")
    if not model_path.exists():
        raise FileNotFoundError(
            "Missing Piper model at app/data/voice.onnx. Add a Piper .onnx model before using TTS."
        )

    # output to stdout
    cmd = ["piper", "--model", str(model_path), "--output_file", "-"]
    proc = subprocess.run(cmd, input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"Piper TTS failed: {proc.stderr.decode('utf-8', errors='ignore')}")
    return proc.stdout


@app.post("/message")
def message(req: MessageRequest):
    t0 = time.perf_counter()

    memory.add_user(req.session_id, req.user_message)

    t_llm0 = time.perf_counter()
    ai_response = agent.respond(memory.get(req.session_id))
    t_llm1 = time.perf_counter()

    memory.add_ai(req.session_id, ai_response)

    t_tts0 = time.perf_counter()
    wav_bytes = _tts_to_wav_bytes(ai_response)
    t_tts1 = time.perf_counter()

    convo = memory.get(req.session_id)
    print("\n--- Conversation Dump ---")
    for idx, msg in enumerate(convo):
        role = "user" if idx % 2 == 0 else "assistant"
        print(f"[{idx:02d}] {role}: {msg}")
    print(f"LLM time: {(t_llm1 - t_llm0):.3f}s")
    print(f"TTS time: {(t_tts1 - t_tts0):.3f}s")
    print(f"Total time: {(time.perf_counter() - t0):.3f}s")
    print("--- End Conversation Dump ---\n")

    # Return wav bytes directly (no URL)
    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            # Provide text in a header (simple) so frontend can still show transcript.
            # If you need more metadata, switch to multipart/mixed or base64-in-JSON.
            "X-Response-Text": ai_response,
        },
    )
