import re
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.base_agent import BaseAgent
from app.memory.session_memory import memory
from app.agent.system_prompt import SYSTEM_PROMPT
from app.tts.piper_wav_tts import synthesize_speech_raw

# ─────────────────────────────────────────────────────────
# TEST MODE
# Set to True to automatically run all test scenarios when
# the server starts. Agent responses print to the console.
# No microphone or audio is used — pure text only.
# Set to False for normal voice operation.
# ─────────────────────────────────────────────────────────
TEST_MODE = False

agent = BaseAgent(system_prompt=SYSTEM_PROMPT)

app = FastAPI(title="MedicalSupportAgent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Startup ──────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    if TEST_MODE:
        print("\n" + "═" * 64)
        print("  TEST MODE IS ON — running all scenarios on startup...")
        print("═" * 64 + "\n")
        # Run synchronously so output is visible before any request
        from app.tests.runner import run_all_scenarios
        from app.tests.scenarios import SCENARIOS
        run_all_scenarios(SCENARIOS, cleanup_after=False)
        print("\n  Test run complete. Server is now ready for requests.\n")


# ─── Models ───────────────────────────────────────────────

class MessageRequest(BaseModel):
    session_id: str
    user_message: str


# ─── Core Endpoints ───────────────────────────────────────

@app.get("/start_session")
def start_session():
    session_id = str(uuid.uuid4())
    memory.init(session_id)
    greeting = "Hello, this is Ana from BelMedic. How can I help you today?"
    memory.add_message(session_id, {"role": "assistant", "content": greeting})
    return {
        "session_id": session_id,
        "greeting": greeting,
    }


@app.post("/message")
async def message(req: MessageRequest):
    """Stream raw PCM audio bytes (16-bit, 22050Hz, Mono)."""
    return StreamingResponse(
        audio_stream_generator(req.session_id, req.user_message),
        media_type="application/octet-stream"
    )


async def audio_stream_generator(session_id: str, user_message: str):
    """
    Collects text chunks from the agent and converts each phrase to raw PCM audio.
    Splits on sentence/clause endings for minimal TTS latency.
    """
    sentence_buffer = ""
    chunk_pattern = re.compile(r'(?<=[.?!,;:])\s+')

    try:
        for text_chunk in agent.respond_stream(session_id, user_message):
            sentence_buffer += text_chunk
            parts = chunk_pattern.split(sentence_buffer)

            if len(parts) > 1:
                to_synthesize  = parts[:-1]
                sentence_buffer = parts[-1]
                for phrase in to_synthesize:
                    if phrase.strip():
                        raw_audio = synthesize_speech_raw(phrase.strip())
                        if raw_audio:
                            yield raw_audio

        # Flush remaining buffer
        if sentence_buffer.strip():
            raw_audio = synthesize_speech_raw(sentence_buffer.strip())
            if raw_audio:
                yield raw_audio

    except Exception:
        fallback = synthesize_speech_raw("I'm sorry, something went wrong. Please try again.")
        if fallback:
            yield fallback


# ─── Debug / Test Endpoints ────────────────────────────────

@app.get("/session/{session_id}/state")
def get_session_state(session_id: str):
    """Return the live state and collected data for a session."""
    ctx      = memory.get_context(session_id)
    messages = memory.get(session_id)
    return {
        **ctx.to_dict(),
        "message_count": len(messages),
    }


@app.get("/session/{session_id}/history")
def get_session_history(session_id: str):
    """Return the full message history for a session."""
    messages = memory.get(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return {"session_id": session_id, "messages": messages}


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Reset a session back to GREETING state, clearing all memory."""
    memory.clear(session_id)
    return {"cleared": True, "session_id": session_id}


@app.get("/test/run")
def run_tests_http(scenario: str = None, cleanup: bool = False):
    """
    Run test scenarios via HTTP and return JSON results.
    ?scenario=full_booking_blood_test  → run one scenario
    ?cleanup=true                      → delete reservations created during test
    """
    if not TEST_MODE:
        raise HTTPException(
            status_code=403,
            detail="Test endpoints are disabled. Set TEST_MODE = True in main.py."
        )

    from app.tests.runner import run_all_scenarios
    from app.tests.scenarios import SCENARIOS

    scenarios_to_run = (
        [s for s in SCENARIOS if s.name == scenario]
        if scenario
        else SCENARIOS
    )

    if not scenarios_to_run:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario}' not found. Available: {[s.name for s in SCENARIOS]}"
        )

    results = run_all_scenarios(scenarios_to_run, cleanup_after=cleanup)
    return {
        "ran": len(results),
        "passed": sum(1 for r in results if not r.get("error")),
        "failed": sum(1 for r in results if r.get("error")),
        "results": results,
    }


@app.get("/test/scenarios")
def list_scenarios():
    """List all available test scenario names and descriptions."""
    from app.tests.scenarios import SCENARIOS
    return [{"name": s.name, "description": s.description} for s in SCENARIOS]
