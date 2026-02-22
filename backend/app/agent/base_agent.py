from openai import OpenAI
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
import json
from datetime import datetime

from app.agent.guardrails import apply_guardrails
from app.agent.tools.service_context import build_service_context
from app.agent.tool_definitions import TOOLS_SCHEMA
from app.memory.session_memory import memory
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

# Load static data once
with open("app/data/reservations.json") as f:
    reservations = json.load(f)

with open("app/data/services.json") as f:
    services = json.load(f)

# Filler phrases to hide database/LLM latency during tool calls
FILLER_PHRASES = {
    "tool_create_reservation": "Just a moment while I confirm that booking in the system.",
    "tool_get_available_slots": "Let me quickly check the calendar for available times.",
    "tool_find_patient_reservations": "Let me pull up your records right now.",
    "tool_check_availability": "Let me see if that specific time is open.",
    "tool_update_reservation": "Give me a second to update your reservation.",
    "tool_delete_reservation": "I'll go ahead and cancel that for you now."
}

class BaseAgent:
    def __init__(self, system_prompt: str):
        self.base_system_prompt = system_prompt
        
        self.tools_map = {
            "tool_create_reservation": tool_create_reservation,
            "tool_find_patient_reservations": tool_find_patient_reservations,
            "tool_update_reservation": tool_update_reservation,
            "tool_delete_reservation": tool_delete_reservation,
            "tool_check_availability": tool_check_availability,
            "tool_get_available_slots": tool_get_available_slots
        }

    def respond_stream(self, session_id: str, user_message: str):
        """
        Generator that yields text chunks, handles tool execution, 
        and updates long-term memory automatically.
        """
        # 1. Guardrails
        guardrail_response = apply_guardrails(user_message)
        if guardrail_response:
            yield guardrail_response
            return

        # 2. Append User Message to Memory
        user_msg_obj = {"role": "user", "content": user_message}
        memory.add_message(session_id, user_msg_obj)
        
        # Retrieve full conversation history (List of Dicts)
        conversation_history = memory.get(session_id)

        # 3. Build Dynamic System Prompt
        now = datetime.now()
        current_datetime_str = now.strftime("%A, %B %d, %Y at %H:%M")

        system_prompt = (
            self.base_system_prompt
            + f"\n\nCURRENT DATE AND TIME: {current_datetime_str}\n"
            + "Use this to interpret relative dates like 'tomorrow', 'next Monday', etc.\n\n"
            + build_service_context()
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)

        # 4. First LLM Stream (Intent & Tool Selection)
        stream = client.chat.completions.create(
            model=OLLAMA_MODEL,
            temperature=0.2,
            messages=messages,
            tools=TOOLS_SCHEMA,
            stream=True
        )

        tool_calls_buffer = [] 
        full_text_response = ""
        emitted_filler = False
        
        for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                full_text_response += delta.content
                yield delta.content

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if len(tool_calls_buffer) <= tc.index:
                        tool_calls_buffer.append({"id": "", "name": "", "arguments": ""})
                    
                    t_buffer = tool_calls_buffer[tc.index]
                    if tc.id: t_buffer["id"] += tc.id
                    if tc.function.name: t_buffer["name"] += tc.function.name
                    if tc.function.arguments: t_buffer["arguments"] += tc.function.arguments
                    
                    # Yield filler audio instantly to hide latency
                    if not emitted_filler and t_buffer["name"] in FILLER_PHRASES:
                        filler = FILLER_PHRASES[t_buffer["name"]]
                        yield filler + " "
                        full_text_response += filler + " "
                        emitted_filler = True

        # 5. Handle Tool Execution
        if tool_calls_buffer:
            # We must save the LLM's Tool Call to Memory so it remembers WHAT it did
            assistant_msg = {
                "role": "assistant",
                "content": full_text_response if full_text_response else None,
                "tool_calls": [
                    {
                        "id": t["id"] or f"call_{t['name']}",
                        "type": "function",
                        "function": {"name": t["name"], "arguments": t["arguments"]}
                    } for t in tool_calls_buffer
                ]
            }
            memory.add_message(session_id, assistant_msg)
            messages.append(assistant_msg)

            # Execute Tools
            for t_call in tool_calls_buffer:
                tool_name = t_call["name"]
                tool_args_str = t_call["arguments"]
                call_id = t_call["id"] or f"call_{tool_name}"

                try:
                    tool_args = json.loads(tool_args_str) if tool_args_str else {}
                    if tool_name in self.tools_map:
                        result_str = self.tools_map[tool_name](**tool_args)
                    else:
                        result_str = json.dumps({"error": f"Unknown tool {tool_name}"})
                except Exception as e:
                    result_str = json.dumps({"error": f"Failed to parse arguments: {str(e)}"})

                # Save Tool Result to Memory
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_str,
                    "name": tool_name
                }
                memory.add_message(session_id, tool_msg)
                messages.append(tool_msg)

            # 6. Final Turn: Interpret tool results
            final_stream = client.chat.completions.create(
                model=OLLAMA_MODEL,
                temperature=0.2,
                messages=messages,
                stream=True
            )
            
            final_text_response = ""
            for chunk in final_stream:
                if chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    final_text_response += text_chunk
                    yield text_chunk
                    
            # Save the final text interpretation to memory
            if final_text_response:
                memory.add_message(session_id, {"role": "assistant", "content": final_text_response})
        else:
            # If no tools were called, just save the standard text response
            if full_text_response:
                memory.add_message(session_id, {"role": "assistant", "content": full_text_response})
