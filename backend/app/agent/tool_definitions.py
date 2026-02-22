"""
JSON Schema definitions for the tools available to the agent.
Used for native tool calling with the OpenAI/Ollama API.
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "tool_create_reservation",
            "description": "Create a new reservation for a patient. ONLY use this after the user has explicitly confirmed the details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string", "description": "The ID of the medical service (e.g., 'srv_01')"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "time": {"type": "string", "description": "Time in HH:MM format"},
                    "patient_name": {"type": "string", "description": "Full name of the patient"},
                    "patient_dob": {"type": "string", "description": "Date of birth in YYYY-MM-DD format"},
                    "patient_email": {"type": "string", "description": "Patient email address"},
                    "patient_phone": {"type": "string", "description": "Patient phone number"}
                },
                "required": ["service_id", "date", "time", "patient_name", "patient_dob", "patient_email", "patient_phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_find_patient_reservations",
            "description": "Find existing reservations for a specific patient by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string", "description": "Full name of the patient to search for"}
                },
                "required": ["patient_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_update_reservation",
            "description": "Update details of an existing reservation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string", "description": "The unique ID of the reservation to update"},
                    "service_id": {"type": "string", "description": "New service ID (optional)"},
                    "date": {"type": "string", "description": "New date in YYYY-MM-DD format (optional)"},
                    "time": {"type": "string", "description": "New time in HH:MM format (optional)"},
                    "patient_name": {"type": "string", "description": "New patient name (optional)"},
                    "patient_dob": {"type": "string", "description": "New date of birth (optional)"}
                },
                "required": ["reservation_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_delete_reservation",
            "description": "Cancel or delete an existing reservation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string", "description": "The unique ID of the reservation to cancel"}
                },
                "required": ["reservation_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_check_availability",
            "description": "Check if a specific date and time slot is available for a service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string", "description": "The ID of the service"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "time": {"type": "string", "description": "Time in HH:MM format"}
                },
                "required": ["service_id", "date", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_available_slots",
            "description": "Get available appointment time slots for a service. Call this as soon as a service is chosen, BEFORE asking the user for their preferred time. Always use today's date as from_date unless the user specified a future date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string", "description": "The ID of the service"},
                    "from_date": {"type": "string", "description": "Date to start searching from (YYYY-MM-DD). Use current date."},
                    "count": {"type": "integer", "description": "How many slots to return, default 5"}
                },
                "required": ["service_id", "from_date"]
            }
        }
    }
]