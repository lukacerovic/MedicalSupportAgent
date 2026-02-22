from enum import Enum
import copy


class ConversationState(Enum):
    GREETING                = "greeting"
    SERVICE_SELECTION       = "service_selection"
    SLOT_SELECTION          = "slot_selection"
    PATIENT_DATA_COLLECTION = "patient_data_collection"
    CONFIRMATION            = "confirmation"
    BOOKING_COMPLETE        = "booking_complete"
    MANAGE_RESERVATION      = "manage_reservation"
    RESCHEDULE              = "reschedule"
    CANCELLATION            = "cancellation"
    GENERAL_INQUIRY         = "general_inquiry"


STATE_TEMPLATES: dict[ConversationState, dict] = {

    ConversationState.GREETING: {},

    ConversationState.SERVICE_SELECTION: {
        "suggested_services": [],
        "selected_service_id": None,
        "selected_service_name": None
    },

    ConversationState.SLOT_SELECTION: {
        "service_id": None,
        "service_name": None,
        "available_slots": [],
        "selected_date": None,
        "selected_time": None
    },

    ConversationState.PATIENT_DATA_COLLECTION: {
        "service_id": None,
        "service_name": None,
        "selected_date": None,
        "selected_time": None,
        "patient_name": None,
        "patient_dob": None,
        "patient_email": None,
        "patient_phone": None,
        "missing_fields": ["patient_name", "patient_dob", "patient_email", "patient_phone"],
        "last_error": None
    },

    ConversationState.CONFIRMATION: {
        "service_id": None,
        "service_name": None,
        "date": None,
        "time": None,
        "patient_name": None,
        "patient_dob": None,
        "patient_email": None,
        "patient_phone": None,
        "user_confirmed": False
    },

    ConversationState.BOOKING_COMPLETE: {
        "reservation_id": None,
        "service_name": None,
        "date": None,
        "time": None,
        "patient_name": None,
        "cancelled": False
    },

    ConversationState.MANAGE_RESERVATION: {
        "lookup_name": None,
        "found_reservations": [],
        "selected_reservation_id": None,
        "intent": None  # "reschedule" | "cancel" | "view"
    },

    ConversationState.RESCHEDULE: {
        "reservation_id": None,
        "service_id": None,
        "service_name": None,
        "current_date": None,
        "current_time": None,
        "available_slots": [],
        "new_date": None,
        "new_time": None
    },

    ConversationState.CANCELLATION: {
        "reservation_id": None,
        "service_name": None,
        "date": None,
        "time": None,
        "user_confirmed": False
    },

    ConversationState.GENERAL_INQUIRY: {
        "topic": None
    }
}


class SessionContext:
    def __init__(self):
        self.state: ConversationState = ConversationState.GREETING
        self.data: dict = {}

    def transition(self, new_state: ConversationState, carry_over: dict = None):
        """
        Move to a new state with a fresh template.
        Optionally carry specific values from previous state data.
        """
        self.state = new_state
        self.data = copy.deepcopy(STATE_TEMPLATES.get(new_state, {}))
        if carry_over:
            for key, value in carry_over.items():
                if key in self.data and value is not None:
                    self.data[key] = value

    def update(self, updates: dict):
        """Patch specific fields in the current state's data."""
        for key, value in updates.items():
            if value is not None:
                self.data[key] = value
        # Auto-refresh missing_fields when in PATIENT_DATA_COLLECTION
        if self.state == ConversationState.PATIENT_DATA_COLLECTION:
            self.data["missing_fields"] = [
                f for f in ["patient_name", "patient_dob", "patient_email", "patient_phone"]
                if not self.data.get(f)
            ]

    def to_prompt_str(self) -> str:
        """Serialize current state + data into a string block for the system prompt."""
        import json
        data_str = json.dumps(self.data, indent=2, ensure_ascii=False)
        rules = self._get_state_rules()
        return (
            f"\n\n═══════════════════════════════════════\n"
            f"CURRENT SESSION STATE: {self.state.value.upper().replace('_', ' ')}\n"
            f"Collected data so far:\n{data_str}\n"
            f"State rules:\n{rules}\n"
            f"═══════════════════════════════════════\n"
        )

    def _get_state_rules(self) -> str:
        rules = {
            ConversationState.GREETING: (
                "- Greet the user warmly and ask how you can help."
            ),
            ConversationState.SERVICE_SELECTION: (
                "- Help the user identify the right BelMedic service.\n"
                "- Do NOT book anything yet. Just identify the service."
            ),
            ConversationState.SLOT_SELECTION: (
                "- Present the available_slots to the user (max 3).\n"
                "- Wait for the user to pick one.\n"
                "- Once user confirms a slot, call tool_check_availability with that date and time."
            ),
            ConversationState.PATIENT_DATA_COLLECTION: (
                "- Collect fields listed in missing_fields one or two at a time, conversationally.\n"
                "- Do NOT re-ask fields that are already non-null above.\n"
                "- If last_error is set, tell the user what went wrong and ask to re-enter that field.\n"
                "- Once ALL fields are non-null, do a single read-back and ask for confirmation."
            ),
            ConversationState.CONFIRMATION: (
                "- Read back all details ONCE and ask 'Shall I confirm this booking?'.\n"
                "- On 'yes', call tool_create_reservation immediately. Do NOT ask again."
            ),
            ConversationState.BOOKING_COMPLETE: (
                "- Booking is complete. Confirm the reservation_id to the user.\n"
                "- Ask if there's anything else you can help with."
            ),
            ConversationState.MANAGE_RESERVATION: (
                "- Show the found_reservations to the user.\n"
                "- Ask if they want to reschedule, cancel, or just view."
            ),
            ConversationState.RESCHEDULE: (
                "- Help the user pick a new slot from available_slots.\n"
                "- Call tool_update_reservation once the new slot is confirmed."
            ),
            ConversationState.CANCELLATION: (
                "- Confirm the cancellation details with the user before calling tool_delete_reservation."
            ),
            ConversationState.GENERAL_INQUIRY: (
                "- Answer the question concisely, then offer to book a relevant BelMedic service."
            ),
        }
        return rules.get(self.state, "- Follow the general guidelines.")

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "data": self.data
        }
