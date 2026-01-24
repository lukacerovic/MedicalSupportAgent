# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app.agent.base_agent import BaseAgent
from app.memory.session_memory import memory
from app.agent.system_prompt import SYSTEM_PROMPT

# Load your AI agent
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
    import uuid

    session_id = str(uuid.uuid4())
    memory.init(session_id)
    return {
        "session_id": session_id,
        "greeting": "Hello, this is Ana from BelMedic. How can I help you today?",
    }


@app.post("/message")
def message(req: MessageRequest):
    """Return audio bytes instead of JSON string."""

    memory.add_user(req.session_id, req.user_message)
    ai_response = agent.respond(memory.get(req.session_id))
    memory.add_ai(req.session_id, ai_response)

    from app.tts.edge_tts import synthesize_speech_mp3

    mp3_bytes = synthesize_speech_mp3(ai_response)

    if not mp3_bytes:
        return Response(
            content=b"edge-tts returned empty audio.",
            status_code=500,
            media_type="text/plain",
        )

    return Response(content=mp3_bytes, media_type="audio/mpeg")
