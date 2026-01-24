import re
import json

with open("app/data/services.json") as f:
    SERVICES = json.load(f)

KEYWORDS = {
    "cardio_check": ["heart", "chest", "pressure", "palpitations"],
    "cardio_ultrasound": ["echo", "ultrasound heart"],
    "internal_medicine": ["fatigue", "fever", "general", "checkup"],
    "blood_tests_basic": ["blood test", "cholesterol", "glucose"],
    "blood_tests_extended": ["extended blood", "liver", "kidney"],
    "neurology_consult": ["headache", "dizziness", "migraine", "numbness"],
    "orthopedic_exam": ["knee", "back", "joint", "shoulder"],
    "abdominal_ultrasound": ["abdomen", "stomach", "liver", "kidney"]
}

def suggest_relevant_services(text: str):
    text = text.lower()
    matched_ids = set()

    for service_id, words in KEYWORDS.items():
        for w in words:
            if re.search(w, text):
                matched_ids.add(service_id)

    return [s for s in SERVICES if s["id"] in matched_ids]
