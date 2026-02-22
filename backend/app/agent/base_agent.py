from openai import OpenAI
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
import json
from datetime import datetime

from app.agent.guardrails import apply_guardrails
from app.agent.tools.service_context import build_service_context
from app.agent.tool_definitions import TOOLS_SCHEMA
from app.agent.tools.reservation_tools import (
    tool_create_reservation,
    tool_find_patient_reservations,
    tool_update_reservation,
    tool_delete_reservation,
    tool_check_availability,
    tool_get_available_slots
)

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"
)

# Load static data once (optional, could be moved to a service)
with open("app/data/reservations.json") as f:
    reservations = json.load(f)

with open("app/data/services.json") as f:
    services = json.load(f)


class BaseAgent:
    def __init__(self, system_prompt: str):
        self.base_system_prompt = system_prompt
        
        # Cleaner dispatch method: Map names to functions
        self.tools_map = {
            "tool_create_reservation": tool_create_reservation,
            "tool_find_patient_reservations": tool_find_patient_reservations,
            "tool_update_reservation": tool_update_reservation,
            "tool_delete_reservation": tool_delete_reservation,
            "tool_check_availability": tool_check_availability,
            "tool_get_available_slots": tool_get_available_slots
        }

    def respond_stream(self, conversation: list[str]):
        """
        Generator that yields text chunks using native tool calling.
        """
        last_user_message = conversation[-1]

        # 1. Check Guardrails (Pre-check)
        guardrail_response = apply_guardrails(last_user_message)
        if guardrail_response:
            yield guardrail_response
            return

        # 2. Build Context with Current Date/Time
        now = datetime.now()
        current_datetime_str = now.strftime("%A, %B %d, %Y at %H:%M")

        system_prompt = (
            self.base_system_prompt
            + f"\n\nCURRENT DATE AND TIME: {current_datetime_str}\n"
            + "Use this to interpret relative dates like 'tomorrow', 'next Monday', etc.\n\n"
            + build_service_context()
        )

        messages = [{"role": "system", "content": system_prompt}]
        for i, msg in enumerate(conversation):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})

        # 3. Stream Response with Native Tools
        stream = client.chat.completions.create(
            model=OLLAMA_MODEL,
            temperature=0.2,
            messages=messages,
            tools=TOOLS_SCHEMA,
            stream=True
        )

        # State for tool accumulation
        tool_calls_buffer = [] 
        
        for chunk in stream:
            delta = chunk.choices[0].delta

            # A. If there's text content, yield it immediately
            if delta.content:
                yield delta.content

            # B. If there are tool calls, accumulate them
            # (Streaming tool calls come in fragments: name, then args chunks)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    # Extend buffer if needed
                    if len(tool_calls_buffer) <= tc.index:
                        tool_calls_buffer.append({
                            "id": "", 
                            "name": "", 
                            "arguments": ""
                        })
                    
                    t_buffer = tool_calls_buffer[tc.index]
                    
                    if tc.id:
                        t_buffer["id"] += tc.id
                    if tc.function.name:
                        t_buffer["name"] += tc.function.name
                    if tc.function.arguments:
                        t_buffer["arguments"] += tc.function.arguments

        # 4. Handle Tool Execution (if any occurred)
        if tool_calls_buffer:
            # We need to execute calls and send results back to LLM
            
            # Append the Assistant's "intent" to call tools
            # (We reconstruct the tool_calls object for the history)
            assistant_msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": t["id"] or "call_default",
                        "type": "function",
                        "function": {
                            "name": t["name"],
                            "arguments": t["arguments"]
                        }
                    } for t in tool_calls_buffer
                ]
            }
            messages.append(assistant_msg)

            # Execute each tool
            for t_call in tool_calls_buffer:
                tool_name = t_call["name"]
                tool_args_str = t_call["arguments"]
                call_id = t_call["id"] or "call_default"

                try:
                    tool_args = json.loads(tool_args_str)
                    
                    if tool_name in self.tools_map:
                        # Cleaner dispatch: Call function directly from map
                        result_str = self.tools_map[tool_name](**tool_args)
                    else:
                        result_str = json.dumps({"error": f"Unknown tool {tool_name}"})
                        
                except Exception as e:
                    result_str = json.dumps({"error": f"Failed to execute: {str(e)}"})

                # Append result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_str
                })

            # 5. Final Turn: Get natural language interpretation
            final_stream = client.chat.completions.create(
                model=OLLAMA_MODEL,
                temperature=0.2,
                messages=messages,
                stream=True
            )
            
            for chunk in final_stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
