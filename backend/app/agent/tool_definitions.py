"""
JSON Schema definitions for the tools available to the agent.
Used for native tool calling with the OpenAI/Ollama API.
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "tool_create_reservation",
            "description": """Create a new reservation for a patient. 
            
            CRITICAL: You MUST have collected ALL of these fields from the user BEFORE calling this tool:
            - service_id: The service they want
            - date and time: From available slots you showed them
            - patient_name: Their FULL name (first AND last name)
            - patient_dob: Their actual date of birth (NOT 1990-01-01 or any placeholder)
            - patient_email: Their real email address
            - patient_phone: Their real phone number
            
            DO NOT call this tool with placeholder, invented, or missing data. If you don't have a field, ASK the user for it.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string", "description": "The ID of the medical service (e.g., 'neurology_consult')"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "time": {"type": "string", "description": "Time in HH:MM format (24-hour)"},
                    "patient_name": {"type": "string", "description": "FULL name (first and last) collected from the user"},
                    "patient_dob": {"type": "string", "description": "Real date of birth in YYYY-MM-DD format collected from the user"},
                    "patient_email": {"type": "string", "description": "Real email address collected from the user"},
                    "patient_phone": {"type": "string", "description": "Real phone number collected from the user"}
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
            "description": """Get available appointment time slots for a service starting from a specific date.
            
            This tool respects clinic operating hours which vary by day and service:
            - Most services: Mon-Thu 9 AM - 9 PM, Fri 9 AM - 5 PM
            - Blood tests: Early morning slots (7 AM - 12 PM) + Saturday mornings
            - Closed: Sundays
            
            Call this BEFORE asking the user for their preferred time so you can show them real options.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string", "description": "The ID of the service"},
                    "from_date": {"type": "string", "description": "Date to start searching from (YYYY-MM-DD). Use current date or user's requested date."},
                    "count": {"type": "integer", "description": "How many slots to return, default 5"}
                },
                "required": ["service_id", "from_date"]
            }
        }
    }
]