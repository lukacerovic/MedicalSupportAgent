import json

def load_services():
    with open("app/data/services.json") as f:
        return json.load(f)

def build_service_context() -> str:
    services = load_services()

    lines = ["BelMedic services (you may ONLY refer to these):"]
    for s in services:
        lines.append(
            f"- {s['name']} (id: {s['id']}): {s['description']} | "
            f"Duration: {s['durationMinutes']} min | Price: {s['price']} EUR"
        )

    return "\n".join(lines)
