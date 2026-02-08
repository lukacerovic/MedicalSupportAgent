# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import re

from app.agent.base_agent import BaseAgent
from app.memory.session_memory import memory
from app.agent.system_prompt import SYSTEM_PROMPT
from app.tts.piper_wav_tts import synthesize_speech_raw, get_wav_header

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
async def message(req: MessageRequest):
    """
    Stream audio bytes as they are generated.
    Reduced latency by processing sentence-by-sentence.
    """
    memory.add_user(req.session_id, req.user_message)
    
    return StreamingResponse(
        audio_stream_generator(req.session_id),
        media_type="audio/wav"
    )

async def audio_stream_generator(session_id: str):
    """
    Generator that yields WAV audio chunks.
    1. Yields WAV Header first.
    2. Consumes text stream from agent.
    3. Buffers text into sentences.
    4. Synthesizes and yields raw audio for each sentence.
    """
    
    # 1. Send WAV Header first so browser recognizes the stream format
    yield get_wav_header()
    
    conversation = memory.get(session_id)
    
    # We need to accumulate the full text to save to memory later
    full_ai_response = ""
    sentence_buffer = ""
    
    # Regex to detect sentence boundaries
    # Matches periods, question marks, exclamation marks followed by space or end of string
    sentence_end_pattern = re.compile(r'(?<=[.!?])\s+')
    
    for text_chunk in agent.respond_stream(conversation):
        full_ai_response += text_chunk
        sentence_buffer += text_chunk
        
        # Check if we have a full sentence
        # We split by the pattern
        parts = sentence_end_pattern.split(sentence_buffer)
        
        if len(parts) > 1:
            # We have at least one complete sentence
            # The last part is the incomplete next sentence
            to_synthesize = parts[:-1]
            sentence_buffer = parts[-1]
            
            for sentence in to_synthesize:
                if sentence.strip():
                    raw_audio = synthesize_speech_raw(sentence)
                    if raw_audio:
                        yield raw_audio
    
    # Process remaining buffer
    if sentence_buffer.strip():
        raw_audio = synthesize_speech_raw(sentence_buffer)
        if raw_audio:
            yield raw_audio
            
    # Update memory with the full response after stream ends
    memory.add_ai(session_id, full_ai_response)
