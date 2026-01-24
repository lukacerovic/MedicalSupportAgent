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
            + "\n\n"
            + TOOL_INSTRUCTIONS
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

        assistant_message = response.choices[0].message.content.strip()

        # Check if model wants to call a tool
        tool_call_match = re.search(
            r'<TOOL_CALL>\s*tool_name:\s*(\S+)\s*parameters:\s*([\s\S]+?)</TOOL_CALL>',
            assistant_message,
            re.IGNORECASE
        )

        if tool_call_match:
            tool_name = tool_call_match.group(1).strip()
            params_text = tool_call_match.group(2).strip()
            
            # Parse parameters (simple YAML-style)
            params = {}
            for line in params_text.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    params[key.strip()] = value.strip()
            
            # Execute tool
            tool_result = self._execute_tool(tool_name, params)
            
            # Remove tool call from response and add result
            clean_response = re.sub(
                r'<TOOL_CALL>[\s\S]+?</TOOL_CALL>',
                '',
                assistant_message
            ).strip()
            
            # Parse tool result and generate natural response
            try:
                result_data = json.loads(tool_result)
                if result_data.get("success"):
                    if "reservation" in result_data:
                        res = result_data["reservation"]
                        return f"{clean_response}\n\nYour appointment is confirmed! Reservation ID: {res['reservationId']}".strip()
                    else:
                        return f"{clean_response}\n\n{result_data.get('message', '')}".strip()
                else:
                    return f"I'm sorry, there was an issue: {result_data.get('error', 'Unknown error')}. Let's try a different time slot."
            except:
                return clean_response if clean_response else "Reservation processed."
        
        return assistant_message

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
