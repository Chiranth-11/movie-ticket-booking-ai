from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Movie(BaseModel):
    id: str
    title: str
    genre: List[str]
    language: str
    duration_mins: int
    rating: float
    poster_url: str
    description: str
    director: str
    cast: List[str]
    release_year: int
    backdrop_url: Optional[str] = None

class Showtime(BaseModel):
    id: str
    movie_id: str
    theater_name: str
    screen_type: str  # e.g., "IMAX 3D", "Dolby Atmos 4K", "Standard"
    screen_number: int
    date: str         # YYYY-MM-DD
    time_slot: str    # e.g., "07:30 PM"
    base_price: float

class Seat(BaseModel):
    id: str           # e.g., "A1", "C5"
    row: str          # "A", "B", etc.
    number: int       # 1 to 10
    tier: str         # "VIP", "Premium", "Standard"
    price: float
    status: str       # "available", "held", "booked", "recommended"

class SeatMapResponse(BaseModel):
    showtime_id: str
    movie_id: str
    movie_title: str
    theater_name: str
    screen_type: str
    date: str
    time_slot: str
    seats: List[Seat]
    total_available: int
    total_seats: int

class BookingRequest(BaseModel):
    showtime_id: str
    seat_ids: List[str]
    customer_name: str
    customer_email: str
    payment_method: str = "Credit Card"
    promo_code: Optional[str] = None

class Booking(BaseModel):
    booking_id: str
    showtime_id: str
    movie_id: str
    movie_title: str
    theater_name: str
    screen_type: str
    date: str
    time_slot: str
    seat_ids: List[str]
    subtotal: float
    discount: float
    taxes_and_fees: float
    total_amount: float
    customer_name: str
    customer_email: str
    payment_method: str
    status: str       # "confirmed", "cancelled"
    booked_at: str
    qr_code_data: str

class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    execution_time_ms: float

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default_session"
    current_movie_id: Optional[str] = None
    current_showtime_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tool_calls: List[ToolCallRecord] = []
    ui_action: Optional[Dict[str, Any]] = None
    session_state: Dict[str, Any] = {}
