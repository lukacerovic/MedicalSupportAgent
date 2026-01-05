from openai import OpenAI
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
import json

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"
)

with open("app/data/reservations.json") as f:
    reservations = json.load(f)
with open("app/data/services.json") as f:
    services = json.load(f)

class BaseAgent:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    def respond(self, conversation: list[str]) -> str:
        """
        conversation: list of strings including previous user and AI messages
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        for i, msg in enumerate(conversation):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})

        # Call LLM
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            temperature=0.2,
            messages=messages
        )

        return response.choices[0].message.content.strip()
