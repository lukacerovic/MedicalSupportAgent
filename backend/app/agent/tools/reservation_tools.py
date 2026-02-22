"""Reservation tools that the LLM can call via structured prompts."""
import json
from app.agent.tools.reservations_store import (
    create_reservation,
    find_reservation_by_id,
    find_reservations_by_patient,
    update_reservation,
    delete_reservation,
    check_slot_availability,
    get_available_slots,
    get_service_duration
)


def tool_create_reservation(
    service_id: str,
    date: str,
    time: str,
    patient_name: str,
    patient_dob: str,
    patient_email: str = None,
    patient_phone: str = None
) -> str:
    """
    Create a new reservation.
    
    Returns JSON string with success/error.
    """
    try:
        # Check slot availability first
        if not check_slot_availability(service_id, date, time):
            return json.dumps({
                "success": False,
                "error": f"The slot {date} at {time} for service {service_id} is already booked."
            })
        
        reservation = create_reservation(
            service_id=service_id,
            date=date,
            time=time,
            patient_name=patient_name,
            patient_dob=patient_dob,
            patient_email=patient_email,
            patient_phone=patient_phone
        )
        
        return json.dumps({
            "success": True,
            "reservation": reservation,
            "message": f"Reservation created successfully with ID {reservation['reservationId']}."
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def tool_find_patient_reservations(patient_name: str) -> str:
    """
    Find all reservations for a patient.
    
    Returns JSON string with reservations list.
    """
    try:
        reservations = find_reservations_by_patient(patient_name)
        return json.dumps({
            "success": True,
            "count": len(reservations),
            "reservations": reservations
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def tool_update_reservation(
    reservation_id: str,
    service_id: str = None,
    date: str = None,
    time: str = None,
    patient_name: str = None,
    patient_dob: str = None
) -> str:
    """
    Update an existing reservation.
    
    Returns JSON string with success/error.
    """
    try:
        # If changing service/date/time, check availability
        if (service_id or date or time):
            existing = find_reservation_by_id(reservation_id)
            if not existing:
                return json.dumps({
                    "success": False,
                    "error": "Reservation not found"
                })
            
            check_service = service_id or existing["serviceId"]
            check_date = date or existing["date"]
            check_time = time or existing["time"]
            
            # Only check if slot changed
            if (check_service != existing["serviceId"] or
                check_date != existing["date"] or
                check_time != existing["time"]):
                
                if not check_slot_availability(check_service, check_date, check_time):
                    return json.dumps({
                        "success": False,
                        "error": f"The new slot {check_date} at {check_time} is already booked."
                    })
        
        updated = update_reservation(
            reservation_id=reservation_id,
            service_id=service_id,
            date=date,
            time=time,
            patient_name=patient_name,
            patient_dob=patient_dob
        )
        
        if updated:
            return json.dumps({
                "success": True,
                "reservation": updated,
                "message": "Reservation updated successfully"
            })
        else:
            return json.dumps({
                "success": False,
                "error": "Reservation not found"
            })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def tool_delete_reservation(reservation_id: str) -> str:
    """
    Cancel/delete a reservation.
    
    Returns JSON string with success/error.
    """
    try:
        success = delete_reservation(reservation_id)
        if success:
            return json.dumps({
                "success": True,
                "message": "Reservation cancelled successfully"
            })
        else:
            return json.dumps({
                "success": False,
                "error": "Reservation not found"
            })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def tool_check_availability(service_id: str, date: str, time: str) -> str:
    """
    Check if a specific slot is available.
    
    Returns JSON string with availability status.
    """
    try:
        available = check_slot_availability(service_id, date, time)
        
        if available:
             duration = get_service_duration(service_id)
             return json.dumps({
                "success": True,
                "available": True,
                "message": f"Slot is available. Note this service requires {duration} minutes."
            })
        else:
            return json.dumps({
                "success": True,
                "available": False,
                "message": "Slot is already booked or overlaps with an existing appointment."
            })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def tool_get_available_slots(service_id: str, from_date: str, count: int = 5) -> str:
    """
    Returns available appointment slots for a service starting from a given date.
    """
    try:
        slots = get_available_slots(service_id, from_date, count)
        if not slots:
            return json.dumps({"success": True, "slots": [], "message": "No available slots found."})
        return json.dumps({"success": True, "slots": slots, "count": len(slots)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})