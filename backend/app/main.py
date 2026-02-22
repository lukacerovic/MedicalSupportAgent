# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import re

from app.agent.base_agent import BaseAgent
from app.memory.session_memory import memory
from app.agent.system_prompt import SYSTEM_PROMPT
from app.tts.piper_wav_tts import synthesize_speech_raw

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
    
    # Store the initial greeting in memory as an assistant message
    greeting = "Hello, this is Ana from BelMedic. How can I help you today?"
    memory.add_message(session_id, {"role": "assistant", "content": greeting})
    
    return {
        "session_id": session_id,
        "greeting": greeting,
    }


@app.post("/message")
async def message(req: MessageRequest):
    """
    Stream raw PCM audio bytes (16-bit, 22050Hz, Mono).
    Frontend must decode this stream manually.
    """
    return StreamingResponse(
        audio_stream_generator(req.session_id, req.user_message),
        media_type="application/octet-stream"
    )

async def audio_stream_generator(session_id: str, user_message: str):
    """
    Generator that yields RAW PCM chunks.
    Splits on commas and sentence endings for faster playback.
    """
    sentence_buffer = ""
    
    # Updated regex: Splits on (. ? ! , : ;) followed by space
    # This creates smaller chunks for the TTS to process faster
    chunk_pattern = re.compile(r'(?<=[.?!,;:])\s+')
    
    for text_chunk in agent.respond_stream(session_id, user_message):
        sentence_buffer += text_chunk
        
        parts = chunk_pattern.split(sentence_buffer)
        
        if len(parts) > 1:
            # We have at least one complete phrase
            to_synthesize = parts[:-1]
            sentence_buffer = parts[-1]
            
            for phrase in to_synthesize:
                if phrase.strip():
                    # Generate audio for this phrase
                    raw_audio = synthesize_speech_raw(phrase.strip())
                    if raw_audio:
                        yield raw_audio
    
    # Process remaining buffer
    if sentence_buffer.strip():
        raw_audio = synthesize_speech_raw(sentence_buffer.strip())
        if raw_audio:
            yield raw_audio
