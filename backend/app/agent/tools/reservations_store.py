import json
import uuid
import threading
from typing import Optional
from datetime import datetime, timedelta

RESERVATIONS_FILE = "app/data/reservations.json"
SERVICES_FILE = "app/data/services.json"
CLINIC_HOURS_FILE = "app/data/clinic_hours.json"
file_lock = threading.Lock()

SLOT_INTERVAL_MINUTES = 15

def load_services() -> list[dict]:
    """Load services to calculate duration."""
    with open(SERVICES_FILE, "r") as f:
        return json.load(f)

def load_reservations() -> list[dict]:
    """Load all reservations from JSON file."""
    with open(RESERVATIONS_FILE, "r") as f:
        return json.load(f)

def load_clinic_hours() -> dict:
    """Load clinic operating hours."""
    with open(CLINIC_HOURS_FILE, "r") as f:
        return json.load(f)

def get_service_duration(service_id: str) -> int:
    """Return the duration of a service in minutes (default 30 if not found)."""
    services = load_services()
    for s in services:
        if s.get("id") == service_id:
            return s.get("durationMinutes", 30)
    return 30

def get_operating_hours_for_day(service_id: str, date: datetime) -> list[tuple[datetime, datetime]]:
    """
    Returns a list of (start, end) datetime tuples for when the clinic is open
    for a specific service on a specific date.
    """
    clinic_hours = load_clinic_hours()
    day_name = date.strftime("%A").lower()
    
    # Check if there's a service-specific exception
    if service_id in clinic_hours.get("service_exceptions", {}):
        hours = clinic_hours["service_exceptions"][service_id].get(day_name, [])
    else:
        hours = clinic_hours["default"].get(day_name, [])
    
    time_windows = []
    for window in hours:
        start_time = datetime.strptime(f"{date.strftime('%Y-%m-%d')} {window['start']}", "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(f"{date.strftime('%Y-%m-%d')} {window['end']}", "%Y-%m-%d %H:%M")
        time_windows.append((start_time, end_time))
    
    return time_windows

def save_reservations(reservations: list[dict]):
    """Save all reservations to JSON file (thread-safe)."""
    with file_lock:
        with open(RESERVATIONS_FILE, "w") as f:
            json.dump(reservations, f, indent=2, ensure_ascii=False)
            f.write("\n")

def check_time_conflict(date: str, requested_time: str, requested_duration: int, reservations: list[dict]) -> bool:
    """
    Check if a requested slot overlaps with ANY existing reservation on the same day.
    """
    req_start = datetime.strptime(f"{date} {requested_time}", "%Y-%m-%d %H:%M")
    req_end = req_start + timedelta(minutes=requested_duration)

    for r in reservations:
        if r.get("date") == date:
            existing_service_id = r.get("serviceId")
            existing_duration = get_service_duration(existing_service_id)
            
            existing_start = datetime.strptime(f"{r['date']} {r['time']}", "%Y-%m-%d %H:%M")
            existing_end = existing_start + timedelta(minutes=existing_duration)

            # Check for ANY overlap
            if req_start < existing_end and req_end > existing_start:
                return True
    
    return False

def create_reservation(
    service_id: str,
    date: str,
    time: str,
    patient_name: str,
    patient_dob: str,
    patient_email: str = None,
    patient_phone: str = None
) -> dict:
    """
    Create a new reservation and save to file with calculated end time.
    """
    # Validate that essential fields are actually provided (not placeholder data)
    if not patient_name or len(patient_name.strip()) < 2:
        raise ValueError("Patient name is required and cannot be empty.")
    
    if not patient_dob or patient_dob == "" or patient_dob == "1990-01-01":
        raise ValueError("Valid patient date of birth is required.")
    
    if not patient_email or patient_email == "" or "@" not in patient_email:
        raise ValueError("Valid patient email is required.")
    
    if not patient_phone or patient_phone == "" or len(patient_phone.strip()) < 6:
        raise ValueError("Valid patient phone number is required.")
    
    duration = get_service_duration(service_id)
    start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(minutes=duration)

    reservation = {
        "reservationId": str(uuid.uuid4()),
        "serviceId": service_id,
        "date": date,
        "time": time,
        "endTime": end_dt.strftime("%H:%M"),
        "patientName": patient_name,
        "patientDOB": patient_dob,
        "patientEmail": patient_email,
        "patientPhone": patient_phone
    }
    
    reservations = load_reservations()
    reservations.append(reservation)
    save_reservations(reservations)
    
    return reservation


def find_reservation_by_id(reservation_id: str) -> Optional[dict]:
    reservations = load_reservations()
    for r in reservations:
        if r.get("reservationId") == reservation_id:
            return r
    return None


def find_reservations_by_patient(patient_name: str) -> list[dict]:
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
    reservations = load_reservations()
    
    for r in reservations:
        if r.get("reservationId") == reservation_id:
            new_service_id = service_id if service_id is not None else r["serviceId"]
            new_date = date if date is not None else r["date"]
            new_time = time if time is not None else r["time"]

            duration = get_service_duration(new_service_id)
            start_dt = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=duration)

            r["serviceId"] = new_service_id
            r["date"] = new_date
            r["time"] = new_time
            r["endTime"] = end_dt.strftime("%H:%M")
            
            if patient_name is not None:
                r["patientName"] = patient_name
            if patient_dob is not None:
                r["patientDOB"] = patient_dob
            
            save_reservations(reservations)
            return r
    
    return None


def delete_reservation(reservation_id: str) -> bool:
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
    Check if a slot is available using actual duration overlap logic
    AND clinic operating hours.
    """
    reservations = load_reservations()
    duration = get_service_duration(service_id)
    
    # Check time conflicts with existing reservations
    has_conflict = check_time_conflict(date, time, duration, reservations)
    if has_conflict:
        return False
    
    # Check if the slot is within clinic operating hours
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    operating_hours = get_operating_hours_for_day(service_id, date_obj)
    
    if not operating_hours:
        return False  # Clinic is closed
    
    requested_start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    requested_end = requested_start + timedelta(minutes=duration)
    
    # Check if requested time falls within any operating window
    for window_start, window_end in operating_hours:
        if requested_start >= window_start and requested_end <= window_end:
            return True
    
    return False

def get_available_slots(service_id: str, from_date: str, count: int = 5) -> list[dict]:
    """
    Returns the next `count` available time slots for a service,
    starting from `from_date`. Uses dynamic clinic hours.
    """
    reservations = load_reservations()
    duration = get_service_duration(service_id)
    available = []
    
    try:
        current_day = datetime.strptime(from_date, "%Y-%m-%d")
    except ValueError:
        current_day = datetime.now()
        
    max_days_to_search = 90

    for _ in range(max_days_to_search):
        if len(available) >= count:
            break

        operating_hours = get_operating_hours_for_day(service_id, current_day)
        
        for window_start, window_end in operating_hours:
            if len(available) >= count:
                break
                
            slot = window_start
            
            while slot < window_end and len(available) < count:
                date_str = slot.strftime("%Y-%m-%d")
                time_str = slot.strftime("%H:%M")
                
                has_conflict = check_time_conflict(date_str, time_str, duration, reservations)
                slot_end = slot + timedelta(minutes=duration)
                
                if not has_conflict and slot_end <= window_end:
                    available.append({
                        "date": date_str,
                        "time": time_str,
                        "day_name": slot.strftime("%A, %B %d")
                    })

                slot += timedelta(minutes=SLOT_INTERVAL_MINUTES)

        current_day += timedelta(days=1)

    return available