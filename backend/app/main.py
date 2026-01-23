from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from app.agent.base_agent import BaseAgent
from app.memory.session_memory import memory
from app.agent.system_prompt import SYSTEM_PROMPT

import time
import uuid
import subprocess
from pathlib import Path

# More concise, call-assistant style prompt


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

    On Windows, piping WAV to stdout ("--output_file -") can be unreliable.
    To be robust, write to a temp WAV on disk and read bytes.

    Assumes `piper` is available on PATH and a model exists at `app/data/voice.onnx`.
    """
    model_path = Path("app/data/voice.onnx")
    if not model_path.exists():
        raise FileNotFoundError(
            "Missing Piper model at app/data/voice.onnx. Add a Piper .onnx model before using TTS."
        )

    out_dir = Path("app/data/_tts_out")
    out_dir.mkdir(parents=True, exist_ok=True)

    wav_path = out_dir / f"tts_{uuid.uuid4().hex}.wav"

    cmd = ["piper", "--model", str(model_path), "--output_file", str(wav_path)]
    proc = subprocess.run(
        cmd,
        input=text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Piper TTS failed: {proc.stderr.decode('utf-8', errors='ignore')}"
        )

    wav_bytes = wav_path.read_bytes()

    # best-effort cleanup
    try:
        wav_path.unlink(missing_ok=True)
    except Exception:
        pass

    return wav_bytes


def _dump_conversation_and_timings(
    session_id: str,
    t_llm0: float,
    t_llm1: float,
    t_tts0: float | None = None,
    t_tts1: float | None = None,
    t0: float | None = None,
):
    convo = memory.get(session_id)
    print("\n--- Conversation Dump ---")
    for idx, msg in enumerate(convo):
        role = "user" if idx % 2 == 0 else "assistant"
        print(f"[{idx:02d}] {role}: {msg}")
    print(f"LLM time: {(t_llm1 - t_llm0):.3f}s")
    if t_tts0 is not None and t_tts1 is not None:
        print(f"TTS time: {(t_tts1 - t_tts0):.3f}s")
    if t0 is not None:
        print(f"Total time: {(time.perf_counter() - t0):.3f}s")
    print("--- End Conversation Dump ---\n")


def _safe_header_value(value: str) -> str:
    """Make a value safe for use in an HTTP header.

    Starlette/uvicorn will error on invalid header characters (e.g., newlines).
    Keep it ASCII-ish and single-line.
    """
    if value is None:
        return ""
    # Remove CR/LF and collapse whitespace
    v = value.replace("\r", " ").replace("\n", " ")
        # Encode to ASCII, replacing non-ASCII characters with '?'
        v = v.encode('ascii', errors='replace').decode('ascii')
    # Hard limit to avoid huge headers
    if len(v) > 1000:
        v = v[:1000] + "…"
    return v


@app.post("/message_text")
def message_text(req: MessageRequest):
    """Debug/helper endpoint: returns text only."""
    t0 = time.perf_counter()

    memory.add_user(req.session_id, req.user_message)

    t_llm0 = time.perf_counter()
    ai_response = agent.respond(memory.get(req.session_id))
    t_llm1 = time.perf_counter()

    memory.add_ai(req.session_id, ai_response)

    _dump_conversation_and_timings(req.session_id, t_llm0, t_llm1, t0=t0)

    return {"response_text": ai_response}


@app.post("/message")
def message(req: MessageRequest):
    """Primary endpoint: returns WAV bytes (audio/wav)."""
    t0 = time.perf_counter()

    memory.add_user(req.session_id, req.user_message)

    t_llm0 = time.perf_counter()
    ai_response = agent.respond(memory.get(req.session_id))
    t_llm1 = time.perf_counter()

    memory.add_ai(req.session_id, ai_response)

    t_tts0 = time.perf_counter()
    wav_bytes = _tts_to_wav_bytes(ai_response)
    t_tts1 = time.perf_counter()

    _dump_conversation_and_timings(req.session_id, t_llm0, t_llm1, t_tts0, t_tts1, t0=t0)

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "X-Response-Text": _safe_header_value(ai_response),
        },
    )
