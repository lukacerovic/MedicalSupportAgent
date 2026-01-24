import json
import uuid
import threading
from typing import Optional
from datetime import datetime

RESERVATIONS_FILE = "app/data/reservations.json"
file_lock = threading.Lock()


def load_reservations() -> list[dict]:
    """Load all reservations from JSON file."""
    with open(RESERVATIONS_FILE, "r") as f:
        return json.load(f)


def save_reservations(reservations: list[dict]):
    """Save all reservations to JSON file (thread-safe)."""
    with file_lock:
        with open(RESERVATIONS_FILE, "w") as f:
            json.dump(reservations, f, indent=2, ensure_ascii=False)
            f.write("\n")


def create_reservation(
    service_id: str,
    date: str,
    time: str,
    patient_name: str,
    patient_dob: str
) -> dict:
    """
    Create a new reservation and save to file.
    
    Args:
        service_id: Service ID (e.g., "blood_tests_basic")
        date: Date in YYYY-MM-DD format
        time: Time in HH:MM format (24-hour)
        patient_name: Full patient name
        patient_dob: Date of birth in YYYY-MM-DD format
    
    Returns:
        The created reservation dict with reservationId
    """
    reservation = {
        "reservationId": str(uuid.uuid4()),
        "serviceId": service_id,
        "date": date,
        "time": time,
        "patientName": patient_name,
        "patientDOB": patient_dob
    }
    
    reservations = load_reservations()
    reservations.append(reservation)
    save_reservations(reservations)
    
    return reservation


def find_reservation_by_id(reservation_id: str) -> Optional[dict]:
    """Find a reservation by its UUID."""
    reservations = load_reservations()
    for r in reservations:
        if r.get("reservationId") == reservation_id:
            return r
    return None


def find_reservations_by_patient(patient_name: str) -> list[dict]:
    """Find all reservations for a given patient name (case-insensitive)."""
    reservations = load_reservations()
    patient_lower = patient_name.lower()
    return [
        r for r in reservations
        if r.get("patientName", "").lower() == patient_lower
    ]


def update_reservation(
    reservation_id: str,
    service_id: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    patient_name: Optional[str] = None,
    patient_dob: Optional[str] = None
) -> Optional[dict]:
    """
    Update an existing reservation by ID.
    Only updates fields that are provided (not None).
    
    Returns:
        Updated reservation dict, or None if not found
    """
    reservations = load_reservations()
    
    for r in reservations:
        if r.get("reservationId") == reservation_id:
            if service_id is not None:
                r["serviceId"] = service_id
            if date is not None:
                r["date"] = date
            if time is not None:
                r["time"] = time
            if patient_name is not None:
                r["patientName"] = patient_name
            if patient_dob is not None:
                r["patientDOB"] = patient_dob
            
            save_reservations(reservations)
            return r
    
    return None


def delete_reservation(reservation_id: str) -> bool:
    """
    Delete a reservation by ID.
    
    Returns:
        True if deleted, False if not found
    """
    reservations = load_reservations()
    original_count = len(reservations)
    
    reservations = [
        r for r in reservations
        if r.get("reservationId") != reservation_id
    ]
    
    if len(reservations) < original_count:
        save_reservations(reservations)
        return True
    
    return False


def check_slot_availability(service_id: str, date: str, time: str) -> bool:
    """
    Check if a slot is available (not already booked).
    
    Args:
        service_id: Service ID
        date: Date in YYYY-MM-DD
        time: Time in HH:MM
    
    Returns:
        True if slot is free, False if already booked
    """
    reservations = load_reservations()
    for r in reservations:
        if (r.get("serviceId") == service_id and
            r.get("date") == date and
            r.get("time") == time):
            return False
    return True
