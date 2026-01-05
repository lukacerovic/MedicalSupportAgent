# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.agent.base_agent import BaseAgent
from app.memory.session_memory import memory

# Load your AI agent
agent = BaseAgent(system_prompt="You are Ana, a medical support agent for BelMedic. Answer user questions about services and reservations politely and informatively.")

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
    import uuid
    session_id = str(uuid.uuid4())
    memory.init(session_id)
    return {"session_id": session_id, "greeting": "Hello, this is Ana from BelMedic. How can I help you today?"}

# Send user message to agent and get response
@app.post("/message")
def message(req: MessageRequest):
    memory.add_user(req.session_id, req.user_message)
    ai_response = agent.respond(memory.get(req.session_id))
    memory.add_ai(req.session_id, ai_response)
    return {"response": ai_response}
