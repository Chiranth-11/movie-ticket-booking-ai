import random
import string
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from ..database import get_connection
from ..models import Booking, BookingRequest
from ..config import PROMO_CODES

class BookingService:
    @staticmethod
    def calculate_pricing(showtime_id: str, seat_ids: List[str], promo_code: Optional[str] = None) -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()
        
        placeholders = ",".join("?" for _ in seat_ids)
        cursor.execute(f"SELECT seat_id, tier, price FROM seats WHERE showtime_id = ? AND seat_id IN ({placeholders})", [showtime_id] + seat_ids)
        seats = cursor.fetchall()
        conn.close()

        subtotal = sum(s["price"] for s in seats)
        discount = 0.0
        promo_info = None

        if promo_code:
            code_upper = promo_code.strip().upper()
            if code_upper in PROMO_CODES:
                promo_data = PROMO_CODES[code_upper]
                if promo_data["type"] == "percent":
                    discount = round((subtotal * promo_data["value"]) / 100.0, 2)
                elif promo_data["type"] == "fixed":
                    discount = min(subtotal, promo_data["value"])
                promo_info = {
                    "code": code_upper,
                    "description": promo_data["description"],
                    "discount_applied": discount
                }

        taxes_and_fees = round((subtotal - discount) * 0.08, 2) # 8% convenience & service tax
        total_amount = round(max(0.0, subtotal - discount + taxes_and_fees), 2)

        return {
            "subtotal": subtotal,
            "discount": discount,
            "taxes_and_fees": taxes_and_fees,
            "total_amount": total_amount,
            "promo_info": promo_info,
            "seats_count": len(seats)
        }

    @staticmethod
    def hold_seats(showtime_id: str, seat_ids: List[str], customer_name: str, duration_mins: int = 5) -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()

        # Check status of seats
        placeholders = ",".join("?" for _ in seat_ids)
        cursor.execute(f"SELECT seat_id, status FROM seats WHERE showtime_id = ? AND seat_id IN ({placeholders})", [showtime_id] + seat_ids)
        existing = cursor.fetchall()

        if len(existing) != len(seat_ids):
            conn.close()
            return {"success": False, "error": "One or more seat numbers are invalid for this showtime."}

        unavailable = [s["seat_id"] for s in existing if s["status"] == "booked"]
        if unavailable:
            conn.close()
            return {"success": False, "error": f"Seats {', '.join(unavailable)} are already booked by other guests."}

        expiry = (datetime.now() + timedelta(minutes=duration_mins)).isoformat()
        cursor.execute(f"""
        UPDATE seats 
        SET status = 'held', held_by = ?, held_until = ?
        WHERE showtime_id = ? AND seat_id IN ({placeholders})
        """, [customer_name, expiry, showtime_id] + seat_ids)
        conn.commit()
        conn.close()

        return {
            "success": True,
            "showtime_id": showtime_id,
            "held_seats": seat_ids,
            "expires_in_minutes": duration_mins,
            "held_until": expiry
        }

    @staticmethod
    def confirm_booking(request: BookingRequest) -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()

        # Get showtime & movie details
        cursor.execute("""
        SELECT s.*, m.title as movie_title, m.id as m_id
        FROM showtimes s
        JOIN movies m ON s.movie_id = m.id
        WHERE s.id = ?
        """, (request.showtime_id,))
        sh = cursor.fetchone()
        if not sh:
            conn.close()
            return {"success": False, "error": f"Showtime {request.showtime_id} not found."}

        # Check seat availability
        placeholders = ",".join("?" for _ in request.seat_ids)
        cursor.execute(f"""
        SELECT seat_id, status, tier, price FROM seats 
        WHERE showtime_id = ? AND seat_id IN ({placeholders})
        """, [request.showtime_id] + request.seat_ids)
        seats = cursor.fetchall()

        if len(seats) != len(request.seat_ids):
            conn.close()
            return {"success": False, "error": "Selected seats are invalid."}

        for s in seats:
            if s["status"] == "booked":
                conn.close()
                return {"success": False, "error": f"Seat {s['seat_id']} is already booked."}

        # Pricing
        pricing = BookingService.calculate_pricing(request.showtime_id, request.seat_ids, request.promo_code)

        # Generate unique booking ID
        random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        booking_id = f"CINE-{datetime.now().strftime('%m%d')}-{random_suffix}"

        # Mark seats as booked
        cursor.execute(f"""
        UPDATE seats 
        SET status = 'booked', held_by = NULL, held_until = NULL
        WHERE showtime_id = ? AND seat_id IN ({placeholders})
        """, [request.showtime_id] + request.seat_ids)

        booked_at = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        qr_code_data = f"TICKET:{booking_id}|MOVIE:{sh['movie_title']}|SEATS:{','.join(request.seat_ids)}|THEATER:{sh['theater_name']}"

        cursor.execute("""
        INSERT INTO bookings (
            booking_id, showtime_id, movie_id, movie_title, theater_name, screen_type,
            date, time_slot, seat_ids, subtotal, discount, taxes_and_fees, total_amount,
            customer_name, customer_email, payment_method, status, booked_at, qr_code_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            booking_id, request.showtime_id, sh["m_id"], sh["movie_title"], sh["theater_name"],
            sh["screen_type"], sh["date"], sh["time_slot"], json.dumps(request.seat_ids),
            pricing["subtotal"], pricing["discount"], pricing["taxes_and_fees"], pricing["total_amount"],
            request.customer_name, request.customer_email, request.payment_method, "confirmed",
            booked_at, qr_code_data
        ))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "booking": Booking(
                booking_id=booking_id,
                showtime_id=request.showtime_id,
                movie_id=sh["m_id"],
                movie_title=sh["movie_title"],
                theater_name=sh["theater_name"],
                screen_type=sh["screen_type"],
                date=sh["date"],
                time_slot=sh["time_slot"],
                seat_ids=request.seat_ids,
                subtotal=pricing["subtotal"],
                discount=pricing["discount"],
                taxes_and_fees=pricing["taxes_and_fees"],
                total_amount=pricing["total_amount"],
                customer_name=request.customer_name,
                customer_email=request.customer_email,
                payment_method=request.payment_method,
                status="confirmed",
                booked_at=booked_at,
                qr_code_data=qr_code_data
            )
        }

    @staticmethod
    def get_booking(booking_id: str) -> Optional[Booking]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        b = dict(row)
        b["seat_ids"] = json.loads(b["seat_ids"])
        return Booking(**b)

    @staticmethod
    def list_all_bookings(limit: int = 20) -> List[Booking]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings ORDER BY booked_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        results = []
        for r in rows:
            b = dict(r)
            b["seat_ids"] = json.loads(b["seat_ids"])
            results.append(Booking(**b))
        return results

    @staticmethod
    def cancel_booking(booking_id: str) -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": f"Booking ID {booking_id} not found."}

        b = dict(row)
        if b["status"] == "cancelled":
            conn.close()
            return {"success": False, "error": f"Booking {booking_id} is already cancelled."}

        seat_ids = json.loads(b["seat_ids"])
        placeholders = ",".join("?" for _ in seat_ids)
        # Release seats
        cursor.execute(f"""
        UPDATE seats SET status = 'available', held_by = NULL, held_until = NULL
        WHERE showtime_id = ? AND seat_id IN ({placeholders})
        """, [b["showtime_id"]] + seat_ids)

        # Update booking status
        cursor.execute("UPDATE bookings SET status = 'cancelled' WHERE booking_id = ?", (booking_id,))
        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"Booking {booking_id} has been successfully cancelled and {len(seat_ids)} seats released.",
            "refund_amount": b["total_amount"],
            "booking_id": booking_id
        }
