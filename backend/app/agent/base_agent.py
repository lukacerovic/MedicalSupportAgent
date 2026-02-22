import json
from datetime import datetime
from openai import OpenAI

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.agent.guardrails import apply_guardrails
from app.agent.tools.service_context import build_service_context
from app.agent.tool_definitions import TOOLS_SCHEMA
from app.memory.session_memory import memory
from app.memory.conversation_state import ConversationState
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

FILLER_PHRASES = {
    "tool_create_reservation":        "Just a moment while I confirm that booking in the system.",
    "tool_get_available_slots":       "Let me quickly check the calendar for available times.",
    "tool_find_patient_reservations": "Let me pull up your records right now.",
    "tool_check_availability":        "Let me see if that specific time is open.",
    "tool_update_reservation":        "Give me a second to update your reservation.",
    "tool_delete_reservation":        "I'll go ahead and cancel that for you now."
}

MAX_HISTORY_MESSAGES = 20


class BaseAgent:
    def __init__(self, system_prompt: str):
        self.base_system_prompt = system_prompt
        self.tools_map = {
            "tool_create_reservation":        tool_create_reservation,
            "tool_find_patient_reservations": tool_find_patient_reservations,
            "tool_update_reservation":        tool_update_reservation,
            "tool_delete_reservation":        tool_delete_reservation,
            "tool_check_availability":        tool_check_availability,
            "tool_get_available_slots":       tool_get_available_slots
        }

    # ─────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────

    def _get_service_name(self, service_id: str) -> str | None:
        """Look up a human-readable service name from services.json."""
        try:
            with open("app/data/services.json") as f:
                services = json.load(f)
            for s in services:
                if s.get("id") == service_id:
                    return s.get("name")
        except Exception:
            pass
        return None

    # ─────────────────────────────────────────
    # State Machine
    # ─────────────────────────────────────────

    def _update_context_from_tool(
        self,
        session_id: str,
        tool_name: str,
        tool_args: dict,
        tool_result: dict
    ):
        """
        Drives the state machine forward based on which tool was called
        and whether it succeeded. All transitions here are deterministic.
        """
        ctx = memory.get_context(session_id)

        # ── tool_get_available_slots ─────────────
        if tool_name == "tool_get_available_slots":
            service_id = tool_args.get("service_id")
            ctx.transition(ConversationState.SLOT_SELECTION, carry_over={
                "service_id":   service_id,
                "service_name": self._get_service_name(service_id)
            })
            ctx.update({"available_slots": tool_result.get("slots", [])})

        # ── tool_check_availability ──────────────
        elif tool_name == "tool_check_availability":
            if tool_result.get("available"):
                # Slot confirmed → move to patient data collection
                ctx.transition(ConversationState.PATIENT_DATA_COLLECTION, carry_over={
                    "service_id":    ctx.data.get("service_id"),
                    "service_name":  ctx.data.get("service_name"),
                    "selected_date": tool_args.get("date"),
                    "selected_time": tool_args.get("time")
                })
            # if not available: stay in SLOT_SELECTION so user picks another

        # ── tool_create_reservation ──────────────
        elif tool_name == "tool_create_reservation":
            if tool_result.get("success"):
                r = tool_result.get("reservation", {})
                ctx.transition(ConversationState.BOOKING_COMPLETE, carry_over={
                    "reservation_id": r.get("reservationId"),
                    "service_name":   ctx.data.get("service_name"),
                    "date":           r.get("date"),
                    "time":           r.get("time"),
                    "patient_name":   r.get("patientName")
                })
            else:
                # Stay in PATIENT_DATA_COLLECTION — surface the error so LLM re-asks
                ctx.update({"last_error": tool_result.get("error")})

        # ── tool_find_patient_reservations ───────
        elif tool_name == "tool_find_patient_reservations":
            ctx.transition(ConversationState.MANAGE_RESERVATION, carry_over={
                "lookup_name": tool_args.get("patient_name")
            })
            ctx.update({"found_reservations": tool_result.get("reservations", [])})

        # ── tool_update_reservation ──────────────
        elif tool_name == "tool_update_reservation":
            if tool_result.get("success"):
                r = tool_result.get("reservation", {})
                ctx.transition(ConversationState.BOOKING_COMPLETE, carry_over={
                    "reservation_id": r.get("reservationId"),
                    "service_name":   ctx.data.get("service_name"),
                    "date":           r.get("date"),
                    "time":           r.get("time"),
                    "patient_name":   r.get("patientName")
                })

        # ── tool_delete_reservation ──────────────
        elif tool_name == "tool_delete_reservation":
            if tool_result.get("success"):
                ctx.transition(ConversationState.BOOKING_COMPLETE)
                ctx.update({"cancelled": True})

    # ─────────────────────────────────────────
    # System Prompt Builder
    # ─────────────────────────────────────────

    def _build_system_prompt(self, session_id: str) -> str:
        """Assemble the full system prompt with live date, services, and session state."""
        now = datetime.now().strftime("%A, %B %d, %Y at %H:%M")
        ctx = memory.get_context(session_id)

        return (
            self.base_system_prompt
            + f"\n\nCURRENT DATE AND TIME: {now}\n"
            + "Use this to interpret relative dates like 'tomorrow', 'next Monday', etc.\n\n"
            + build_service_context()
            + ctx.to_prompt_str()
        )

    # ─────────────────────────────────────────
    # Main Entry Point
    # ─────────────────────────────────────────

    def respond_stream(self, session_id: str, user_message: str):
        """
        Generator: yields text chunks, executes tools, drives the state machine,
        and keeps memory bounded.
        """
        # Expire old sessions on every request
        memory.cleanup_expired()

        # 1. Guardrails
        guardrail_response = apply_guardrails(user_message)
        if guardrail_response:
            yield guardrail_response
            return

        # 2. Transition out of GREETING on first real user message
        ctx = memory.get_context(session_id)
        if ctx.state == ConversationState.GREETING:
            ctx.transition(ConversationState.SERVICE_SELECTION)

        # 3. Save user message
        memory.add_message(session_id, {"role": "user", "content": user_message})

        # 4. Build message list (capped history to avoid context overflow)
        conversation_history = memory.get(session_id)[-MAX_HISTORY_MESSAGES:]
        system_prompt = self._build_system_prompt(session_id)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)

        # 5. First LLM stream — intent detection + tool selection
        try:
            stream = client.chat.completions.create(
                model=OLLAMA_MODEL,
                temperature=0.2,
                messages=messages,
                tools=TOOLS_SCHEMA,
                stream=True
            )
        except Exception:
            yield "I'm sorry, I'm having trouble connecting right now. Please try again in a moment."
            return

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
                    if tc.id:               t_buffer["id"]        += tc.id
                    if tc.function.name:    t_buffer["name"]      += tc.function.name
                    if tc.function.arguments: t_buffer["arguments"] += tc.function.arguments

                    # Emit filler instantly to mask tool latency
                    if not emitted_filler and t_buffer["name"] in FILLER_PHRASES:
                        filler = FILLER_PHRASES[t_buffer["name"]]
                        yield filler + " "
                        full_text_response += filler + " "
                        emitted_filler = True

        # 6. Tool execution
        if tool_calls_buffer:
            assistant_msg = {
                "role": "assistant",
                "content": full_text_response if full_text_response else None,
                "tool_calls": [
                    {
                        "id":   t["id"] or f"call_{t['name']}",
                        "type": "function",
                        "function": {"name": t["name"], "arguments": t["arguments"]}
                    } for t in tool_calls_buffer
                ]
            }
            memory.add_message(session_id, assistant_msg)
            messages.append(assistant_msg)

            for t_call in tool_calls_buffer:
                tool_name    = t_call["name"]
                tool_args_str = t_call["arguments"]
                call_id      = t_call["id"] or f"call_{tool_name}"

                try:
                    tool_args = json.loads(tool_args_str) if tool_args_str else {}
                    if tool_name in self.tools_map:
                        result_str = self.tools_map[tool_name](**tool_args)
                    else:
                        result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})
                except Exception as e:
                    result_str = json.dumps({"error": f"Tool execution failed: {str(e)}"})

                # Drive the state machine
                try:
                    result_dict = json.loads(result_str)
                    self._update_context_from_tool(session_id, tool_name, tool_args, result_dict)
                except Exception:
                    pass  # State machine errors must never break the stream

                tool_msg = {
                    "role":         "tool",
                    "tool_call_id": call_id,
                    "content":      result_str,
                    "name":         tool_name
                }
                memory.add_message(session_id, tool_msg)
                messages.append(tool_msg)

            # 7. Final LLM stream — interpret tool results and respond
            try:
                final_stream = client.chat.completions.create(
                    model=OLLAMA_MODEL,
                    temperature=0.2,
                    messages=messages,
                    stream=True
                )
            except Exception:
                yield "I retrieved the information but I'm having trouble responding. Please try again."
                return

            final_text_response = ""
            for chunk in final_stream:
                if chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    final_text_response += text_chunk
                    yield text_chunk

            if final_text_response:
                memory.add_message(session_id, {"role": "assistant", "content": final_text_response})

        else:
            # No tools called — plain text response
            if full_text_response:
                memory.add_message(session_id, {"role": "assistant", "content": full_text_response})
