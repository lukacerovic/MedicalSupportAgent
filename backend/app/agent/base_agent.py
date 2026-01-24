from openai import OpenAI
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
import json

# NEW imports
from app.agent.guardrails import apply_guardrails
from app.agent.tools.service_context import build_service_context

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"
)

# Load static data once
with open("app/data/reservations.json") as f:
    reservations = json.load(f)

with open("app/data/services.json") as f:
    services = json.load(f)


class BaseAgent:
    def __init__(self, system_prompt: str):
        self.base_system_prompt = system_prompt

    def respond(self, conversation: list[str]) -> str:
        """
        conversation: list of strings including previous user and AI messages
        """

        last_user_message = conversation[-1]

        guardrail_response = apply_guardrails(last_user_message)
        if guardrail_response:
            return guardrail_response

        system_prompt = (
            self.base_system_prompt
            + "\n\n"
            + build_service_context()
        )

        messages = [{"role": "system", "content": system_prompt}]

        for i, msg in enumerate(conversation):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})

        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            temperature=0.2,
            messages=messages
        )

        return response.choices[0].message.content.strip()
