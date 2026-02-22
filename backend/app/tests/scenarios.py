from dataclasses import dataclass


@dataclass
class Scenario:
    name: str
    description: str
    turns: list[str]   # only the USER side — agent responds live


# ─────────────────────────────────────────────────────────
# Each scenario is a realistic scripted user conversation.
# The runner feeds these messages one by one to the agent
# and captures the full text response + state after each turn.
# ─────────────────────────────────────────────────────────

SCENARIOS: list[Scenario] = [

    # 1 ── Full happy path: book a blood test end-to-end
    Scenario(
        name="full_booking_blood_test",
        description="User books a Basic Blood Test, collects all patient fields, confirms.",
        turns=[
            "Hi, I'd like to book a basic blood test",
            "Let's go with the first available slot you have",
            "My name is Marko Petrovic",
            "I was born on March 22nd 1988",
            "marko.petrovic@test.com",
            "+381641234567",
            "Yes, please confirm the booking",
        ]
    ),

    # 2 ── Full happy path: cardiology exam
    Scenario(
        name="full_booking_cardiology",
        description="User with heart palpitations books a Cardiology Examination end-to-end.",
        turns=[
            "I've been having heart palpitations lately, what do you recommend?",
            "Yes, I'd like to book the cardiology examination",
            "Give me the first available slot",
            "Ana Jovanovic",
            "June 10th 1992",
            "ana.jovanovic@belmedic.test",
            "+381652345678",
            "Yes, that's correct, confirm it",
        ]
    ),

    # 3 ── Emergency guardrail fires immediately
    Scenario(
        name="emergency_guardrail",
        description="User reports severe chest pain — guardrail must fire before LLM.",
        turns=[
            "I have severe chest pain and I can't breathe properly",
        ]
    ),

    # 4 ── Medical advice guardrail fires
    Scenario(
        name="medical_advice_guardrail",
        description="User asks for diagnosis and medication — guardrail redirects to services.",
        turns=[
            "Can you diagnose what I have? I think I need some medication for my headaches",
        ]
    ),

    # 5 ── View existing reservations
    Scenario(
        name="view_reservations",
        description="Existing patient wants to see their upcoming appointments.",
        turns=[
            "I'd like to check if I have any upcoming appointments",
            "Marko Petrovic",
        ]
    ),

    # 6 ── Cancel a reservation
    Scenario(
        name="cancel_reservation",
        description="Patient cancels an existing reservation by name lookup.",
        turns=[
            "I want to cancel one of my appointments",
            "My name is Marko Petrovic",
            "Cancel the first one please",
            "Yes, I confirm the cancellation",
        ]
    ),

    # 7 ── General service inquiry (no booking intent)
    Scenario(
        name="general_inquiry",
        description="User asks about services and preparation with no immediate booking.",
        turns=[
            "What abdominal services do you offer?",
            "How long does the abdominal ultrasound take and do I need to prepare?",
            "That's helpful, thank you",
        ]
    ),

    # 8 ── Neurology booking after symptom description
    Scenario(
        name="symptom_to_neurology_booking",
        description="User describes neurological symptoms, agent recommends and books consult.",
        turns=[
            "I've had persistent headaches and dizziness for two weeks",
            "Let's go with the neurology consultation",
            "Any slot next week is fine",
            "Stefan Nikolic",
            "November 3rd 1985",
            "stefan.nikolic@gmail.com",
            "+381661112233",
            "Yes confirm",
        ]
    ),

    # 9 ── Partial info then correction mid-flow
    Scenario(
        name="booking_with_field_correction",
        description="User gives a wrong email then corrects it — agent should not re-read all fields.",
        turns=[
            "I want to book an internal medicine consultation",
            "First available slot please",
            "Jelena Savic",
            "April 15th 1995",
            "jelena.wrong@typo",        # intentionally malformed
            "Sorry, it's jelena.savic@gmail.com",
            "+381609988776",
            "Yes, confirm",
        ]
    ),

]
