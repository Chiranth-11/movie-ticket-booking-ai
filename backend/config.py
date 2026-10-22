import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")

# App configurations
APP_NAME = "CineAgent AI - Movie Ticket Booking System"
APP_VERSION = "1.0.0"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# LLM Providers (Optional for external LLM fallback)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ACTIVE_LLM_PROVIDER = "gemini" if GEMINI_API_KEY else ("openai" if OPENAI_API_KEY else "autonomous_builtin")

# Database
DB_FILE = BASE_DIR / "cinema_booking.db"

# Active Promo Codes
PROMO_CODES = {
    "WELCOME20": {"type": "percent", "value": 20, "description": "20% off for new customers"},
    "CINE10": {"type": "percent", "value": 10, "description": "10% off your entire booking"},
    "POPCORN5": {"type": "fixed", "value": 5.0, "description": "$5 flat discount on any ticket bundle"}
}

# Pricing Tiers
SEAT_TIER_PRICING = {
    "VIP": 22.0,      # Luxury Leather Recliners (Rows A, B)
    "Premium": 16.0,  # Center Optimal View (Rows C, D)
    "Standard": 12.0  # Front & Value Seats (Rows E, F)
}
