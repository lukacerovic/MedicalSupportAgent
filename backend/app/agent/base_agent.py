from openai import OpenAI
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
import json
import re

from app.agent.guardrails import apply_guardrails
from app.agent.tools.service_context import build_service_context
from app.agent.tools.reservation_tools import (
    tool_create_reservation,
    tool_find_patient_reservations,
    tool_update_reservation,
    tool_delete_reservation,
    tool_check_availability
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


TOOL_INSTRUCTIONS = """

You have access to reservation tools. When you need to create, update, find, or cancel reservations, use these tools by writing:

<TOOL_CALL>
tool_name: <name>
parameters:
  param1: value1
  param2: value2
</TOOL_CALL>

Available tools:

1. tool_create_reservation
   Parameters: service_id, date (YYYY-MM-DD), time (HH:MM), patient_name, patient_dob (YYYY-MM-DD)
   Use: Create a new reservation after user confirms all details

2. tool_find_patient_reservations
   Parameters: patient_name
   Use: Find existing reservations for a patient

3. tool_update_reservation
   Parameters: reservation_id (required), service_id (optional), date (optional), time (optional), patient_name (optional), patient_dob (optional)
   Use: Update an existing reservation

4. tool_delete_reservation
   Parameters: reservation_id
   Use: Cancel/delete a reservation

5. tool_check_availability
   Parameters: service_id, date (YYYY-MM-DD), time (HH:MM)
   Use: Check if a slot is available before suggesting it

IMPORTANT:
- Always collect patient_name, patient_dob, service_id, date, and time BEFORE creating a reservation
- After collecting all info, provide a natural confirmation (e.g., "So to confirm, I'll schedule a Basic Blood Test for Marko on January 28th at 10:00—does that work?")
- Only call tool_create_reservation after the user confirms (any variation of yes/correct/that's fine)
- If user says no or wants changes, ask what to adjust
"""


class BaseAgent:
    def __init__(self, system_prompt: str):
        self.base_system_prompt = system_prompt

    def respond(self, conversation: list[str]) -> str:
        """Legacy non-streaming response"""
        full_response = ""
        for chunk in self.respond_stream(conversation):
            full_response += chunk
        return full_response

    def respond_stream(self, conversation: list[str]):
        """
        Generator that yields text chunks. 
        Handles buffering for tool calls internally to avoid streaming tool XML to the user.
        """

        last_user_message = conversation[-1]

        guardrail_response = apply_guardrails(last_user_message)
        if guardrail_response:
            yield guardrail_response
            return

        system_prompt = (
            self.base_system_prompt
            + "\n\n"
            + build_service_context()
            + "\n\n"
            + TOOL_INSTRUCTIONS
        )

        messages = [{"role": "system", "content": system_prompt}]

        for i, msg in enumerate(conversation):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})

        response_stream = client.chat.completions.create(
            model=OLLAMA_MODEL,
            temperature=0.2,
            messages=messages,
            stream=True
        )

        # Buffer to detect tool calls or accumulate sentence fragments
        buffer = ""
        is_tool_call_potential = False
        
        for chunk in response_stream:
            content = chunk.choices[0].delta.content or ""
            if not content:
                continue
                
            buffer += content
            
            # Check if we might be starting a tool call
            if "<" in buffer and not is_tool_call_potential:
                if "<TOOL_CALL>" in buffer:
                    is_tool_call_potential = True
                elif len(buffer) > 20 and "<TOOL_CALL>" not in buffer:
                     # False alarm, flush buffer
                     yield buffer
                     buffer = ""
            
            # If we are strictly in text mode (no pending tool start), yield content
            if not is_tool_call_potential and "<" not in buffer:
                yield buffer
                buffer = ""

            # Check for completed tool call
            if "</TOOL_CALL>" in buffer:
                # Extract and execute tool
                tool_call_match = re.search(
                    r'<TOOL_CALL>\s*tool_name:\s*(\S+)\s*parameters:\s*([\s\S]+?)</TOOL_CALL>',
                    buffer,
                    re.IGNORECASE
                )
                
                if tool_call_match:
                    tool_name = tool_call_match.group(1).strip()
                    params_text = tool_call_match.group(2).strip()
                    
                    params = {}
                    for line in params_text.split('\n'):
                        line = line.strip()
                        if ':' in line:
                            key, value = line.split(':', 1)
                            params[key.strip()] = value.strip()
                    
                    # Yield a filler message if needed, or just silence while working
                    # yield "Checking that for you..." 
                    
                    tool_result = self._execute_tool(tool_name, params)
                    
                    # Clean buffer of the tool call tag
                    buffer = re.sub(r'<TOOL_CALL>[\s\S]+?</TOOL_CALL>', '', buffer).strip()
                    if buffer:
                        yield buffer
                        buffer = ""

                    # Now generate natural response based on tool result
                    # We inject the tool result back into conversation and stream the interpretation
                    tool_followup_messages = messages + [
                        {"role": "assistant", "content": f"<TOOL_CALL>...executed...</TOOL_CALL>"},
                        {"role": "system", "content": f"Tool Result: {tool_result}. content: Please formulate a natural response to the user based on this result."}
                    ]
                    
                    followup_stream = client.chat.completions.create(
                        model=OLLAMA_MODEL,
                        temperature=0.2,
                        messages=tool_followup_messages,
                        stream=True
                    )
                    
                    for f_chunk in followup_stream:
                        f_content = f_chunk.choices[0].delta.content or ""
                        yield f_content
                    
                    return # End after tool response

        # Flush any remaining buffer
        if buffer and not is_tool_call_potential:
            yield buffer

    def _execute_tool(self, tool_name: str, params: dict) -> str:
        """Execute a tool and return JSON result."""
        try:
            if tool_name == "tool_create_reservation":
                return tool_create_reservation(
                    service_id=params.get("service_id"),
                    date=params.get("date"),
                    time=params.get("time"),
                    patient_name=params.get("patient_name"),
                    patient_dob=params.get("patient_dob")
                )
            elif tool_name == "tool_find_patient_reservations":
                return tool_find_patient_reservations(
                    patient_name=params.get("patient_name")
                )
            elif tool_name == "tool_update_reservation":
                return tool_update_reservation(
                    reservation_id=params.get("reservation_id"),
                    service_id=params.get("service_id"),
                    date=params.get("date"),
                    time=params.get("time"),
                    patient_name=params.get("patient_name"),
                    patient_dob=params.get("patient_dob")
                )
            elif tool_name == "tool_delete_reservation":
                return tool_delete_reservation(
                    reservation_id=params.get("reservation_id")
                )
            elif tool_name == "tool_check_availability":
                return tool_check_availability(
                    service_id=params.get("service_id"),
                    date=params.get("date"),
                    time=params.get("time")
                )
            else:
                return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
