import os
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import APP_NAME, APP_VERSION, ACTIVE_LLM_PROVIDER
from .database import init_db
from .models import (
    BookingRequest, ChatRequest, ChatResponse,
    Movie, Showtime, SeatMapResponse
)
from .services.movie_service import MovieService
from .services.booking_service import BookingService
from .agent.core import agent_instance
from .agent.tools import AVAILABLE_TOOLS_SPECS

# Path definitions
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Agentic AI Movie Ticket Booking System - ReAct Loop, Tool Execution, Live Seating Chart"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

# ==================== MOVIE & SHOWTIME ENDPOINTS ====================

@app.get("/api/movies")
def get_movies(
    query: Optional[str] = Query(default=None, description="Search keyword for title or director"),
    genre: Optional[str] = Query(default=None, description="Filter by genre (Sci-Fi, Action, etc.)"),
    min_rating: Optional[float] = Query(default=None, description="Minimum rating filter")
):
    q_str = query if isinstance(query, str) else None
    g_str = genre if isinstance(genre, str) else None
    r_float = min_rating if isinstance(min_rating, (int, float)) else None
    return MovieService.list_movies(query=q_str, genre=g_str, min_rating=r_float)

@app.get("/api/movies/{movie_id}")
def get_movie_detail(movie_id: str):
    movie = MovieService.get_movie(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie

@app.get("/api/showtimes")
def get_showtimes(
    movie_id: Optional[str] = Query(default=None, description="Filter by movie ID"),
    date: Optional[str] = Query(default=None, description="Filter by date (YYYY-MM-DD)")
):
    m_id = movie_id if isinstance(movie_id, str) else None
    d_str = date if isinstance(date, str) else None
    return MovieService.get_showtimes(movie_id=m_id, date=d_str)

@app.get("/api/showtimes/{showtime_id}/seats")
def get_seat_map(showtime_id: str):
    seat_map = MovieService.get_seat_map(showtime_id)
    if not seat_map:
        raise HTTPException(status_code=404, detail="Showtime not found")
    return seat_map

# ==================== BOOKING & PRICING ENDPOINTS ====================

@app.post("/api/pricing")
def calculate_pricing(payload: dict):
    showtime_id = payload.get("showtime_id")
    seat_ids = payload.get("seat_ids", [])
    promo_code = payload.get("promo_code")
    if not showtime_id or not seat_ids:
        raise HTTPException(status_code=400, detail="showtime_id and seat_ids are required")
    return BookingService.calculate_pricing(showtime_id, seat_ids, promo_code)

@app.post("/api/bookings")
def create_booking(request: BookingRequest):
    result = BookingService.confirm_booking(request)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to book tickets"))
    return result["booking"]

@app.get("/api/bookings")
def list_bookings():
    return BookingService.list_all_bookings()

@app.get("/api/bookings/{booking_id}")
def get_booking(booking_id: str):
    b = BookingService.get_booking(booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    return b

@app.post("/api/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str):
    result = BookingService.cancel_booking(booking_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

# ==================== AGENTIC AI ENDPOINTS ====================

@app.post("/api/agent/chat", response_model=ChatResponse)
def chat_with_agent(request: ChatRequest):
    return agent_instance.chat(request)

@app.get("/api/agent/tools")
def get_agent_tools():
    return {
        "status": "active",
        "agent_name": "CineAgent ReAct Concierge",
        "llm_provider": ACTIVE_LLM_PROVIDER,
        "tools_count": len(AVAILABLE_TOOLS_SPECS),
        "tools": AVAILABLE_TOOLS_SPECS
    }

@app.get("/api/agent/stats")
def get_system_stats():
    return {
        "system": APP_NAME,
        "version": APP_VERSION,
        "agent_engine": "Autonomous ReAct + Tool Dispatcher",
        "active_provider": ACTIVE_LLM_PROVIDER,
        "database": "SQLite (Local Persistent)"
    }

# ==================== STATIC FILES & WEB UI ====================

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_frontend_index():
        return FileResponse(FRONTEND_DIR / "index.html")
