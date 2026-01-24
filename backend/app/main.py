# app/main.py
from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app.agent.base_agent import BaseAgent
from app.agent.system_prompt import SYSTEM_PROMPT
from app.memory.session_memory import memory

# TTS (backend-side)
from app.tts.piper_tts import synthesize_speech_mp3


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


# Request model
class MessageRequest(BaseModel):
    session_id: str
    user_message: str


# Start new session
@app.get("/start_session")
def start_session():
    session_id = str(uuid.uuid4())
    memory.init(session_id)

    greeting_text = "Hello, this is Ana from BelMedic. How can I help you today?"
    audio_bytes = synthesize_speech_mp3(greeting_text)

    # We return the session id in a response header so frontend can still store it,
    # while the body is audio.
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"X-Session-Id": session_id},
    )


# Send user message to agent and get response
@app.post("/message")
def message(req: MessageRequest):
    memory.add_user(req.session_id, req.user_message)
    ai_response_text = agent.respond(memory.get(req.session_id))
    memory.add_ai(req.session_id, ai_response_text)

    audio_bytes = synthesize_speech_mp3(ai_response_text)
    return Response(content=audio_bytes, media_type="audio/mpeg")
