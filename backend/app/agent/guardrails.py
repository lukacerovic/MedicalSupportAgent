from app.agent.tools.service_matcher import suggest_relevant_services

EMERGENCY_WORDS = [
    "can't breathe", "chest pain", "unconscious", "severe bleeding"
]

MEDICAL_ADVICE_WORDS = [
    "diagnose", "what do i have", "should i take", "medication", "dose"
]

def apply_guardrails(user_text: str):
    text = user_text.lower()

    if any(w in text for w in EMERGENCY_WORDS):
        services = suggest_relevant_services(text)
        extra = f" After emergency care, you may book {services[0]['name']}." if services else ""
        return (
            "This may be a medical emergency. "
            "Please contact emergency services immediately."
            + extra
        )

    if any(w in text for w in MEDICAL_ADVICE_WORDS):
        services = suggest_relevant_services(text)
        if services:
            return (
                "I’m not a doctor and can’t provide medical advice. "
                f"A suitable next step could be {services[0]['name']}. "
                "Would you like me to help you schedule it?"
            )

        return (
            "I’m not a doctor and can’t provide medical advice. "
            "I recommend an Internal Medicine Consultation."
        )

    return None
