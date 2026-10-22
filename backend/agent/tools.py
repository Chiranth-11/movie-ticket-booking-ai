import time
from typing import Dict, Any, List, Optional
from ..services.movie_service import MovieService
from ..services.booking_service import BookingService
from ..models import BookingRequest, ToolCallRecord

# Tool Declarations / Specifications
AVAILABLE_TOOLS_SPECS = [
    {
        "name": "search_movies",
        "description": "Search the movie catalog by title query, genre, or minimum rating.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term for movie title or director."},
                "genre": {"type": "string", "description": "Genre like Sci-Fi, Action, Animation, Drama."},
                "min_rating": {"type": "number", "description": "Minimum IMDb/audience rating (e.g. 8.5)."}
            }
        }
    },
    {
        "name": "get_showtimes",
        "description": "Retrieve available showtimes, dates, screens (IMAX 3D, Dolby Atmos, Standard), and theaters for a movie.",
        "parameters": {
            "type": "object",
            "properties": {
                "movie_id": {"type": "string", "description": "Movie ID (e.g., 'mov-inception') or movie title."},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format (optional)."}
            },
            "required": ["movie_id"]
        }
    },
    {
        "name": "get_seat_map",
        "description": "Fetch the current interactive seat layout, pricing tiers, and availability status (available, held, booked) for a specific showtime.",
        "parameters": {
            "type": "object",
            "properties": {
                "showtime_id": {"type": "string", "description": "Unique showtime identifier (e.g., 'sht-101')."}
            },
            "required": ["showtime_id"]
        }
    },
    {
        "name": "recommend_seats",
        "description": "Intelligently analyze the seat layout and suggest the best adjacent seats based on tier preference (VIP, Premium, Standard) and viewing angle.",
        "parameters": {
            "type": "object",
            "properties": {
                "showtime_id": {"type": "string", "description": "Showtime ID to inspect."},
                "count": {"type": "integer", "description": "Number of tickets needed (e.g., 1, 2, 4).", "default": 2},
                "preferred_tier": {"type": "string", "description": "Desired tier: 'VIP', 'Premium', or 'Standard'."}
            },
            "required": ["showtime_id"]
        }
    },
    {
        "name": "hold_seats",
        "description": "Temporarily lock selected seats for 5 minutes while the customer prepares payment.",
        "parameters": {
            "type": "object",
            "properties": {
                "showtime_id": {"type": "string", "description": "Showtime ID."},
                "seat_ids": {"type": "array", "items": {"type": "string"}, "description": "List of seat IDs like ['A3', 'A4']."},
                "customer_name": {"type": "string", "description": "Name of guest holding the seats."}
            },
            "required": ["showtime_id", "seat_ids"]
        }
    },
    {
        "name": "apply_promo_code",
        "description": "Validate a promotional discount code (e.g., WELCOME20, CINE10, POPCORN5) and compute pricing breakdown.",
        "parameters": {
            "type": "object",
            "properties": {
                "showtime_id": {"type": "string", "description": "Showtime ID."},
                "seat_ids": {"type": "array", "items": {"type": "string"}, "description": "List of seat IDs."},
                "promo_code": {"type": "string", "description": "Coupon or promo code string."}
            },
            "required": ["showtime_id", "seat_ids", "promo_code"]
        }
    },
    {
        "name": "confirm_booking",
        "description": "Finalize the ticket reservation, lock seats permanently, and generate the confirmed booking receipt with digital pass data.",
        "parameters": {
            "type": "object",
            "properties": {
                "showtime_id": {"type": "string", "description": "Showtime ID."},
                "seat_ids": {"type": "array", "items": {"type": "string"}, "description": "List of seat IDs to book."},
                "customer_name": {"type": "string", "description": "Customer full name.", "default": "Guest Cinephile"},
                "customer_email": {"type": "string", "description": "Customer email.", "default": "guest@cinema.com"},
                "promo_code": {"type": "string", "description": "Optional promo code to apply."},
                "payment_method": {"type": "string", "description": "Payment method (Credit Card, Apple Pay, PayPal).", "default": "Credit Card"}
            },
            "required": ["showtime_id", "seat_ids"]
        }
    },
    {
        "name": "lookup_booking",
        "description": "Look up an existing booking ticket by its booking ID (e.g., 'CINE-1022-XYZ12').",
        "parameters": {
            "type": "object",
            "properties": {
                "booking_id": {"type": "string", "description": "Unique booking code."}
            },
            "required": ["booking_id"]
        }
    },
    {
        "name": "cancel_booking",
        "description": "Cancel an active movie booking and release the held seats back to the public pool.",
        "parameters": {
            "type": "object",
            "properties": {
                "booking_id": {"type": "string", "description": "Unique booking code to cancel."}
            },
            "required": ["booking_id"]
        }
    },
    {
        "name": "recommend_movies",
        "description": "Provide curated movie suggestions based on customer mood, vibe, or genres.",
        "parameters": {
            "type": "object",
            "properties": {
                "mood": {"type": "string", "description": "Vibe or mood (e.g. 'mind-bending', 'dark thriller', 'heartwarming family', 'action spectacle')."},
                "preferences": {"type": "string", "description": "Any additional preferences."}
            },
            "required": ["mood"]
        }
    }
]

class ToolExecutor:
    @staticmethod
    def execute(tool_name: str, arguments: Dict[str, Any]) -> ToolCallRecord:
        start_time = time.time()
        result: Any = None

        try:
            if tool_name == "search_movies":
                result = MovieService.list_movies(
                    query=arguments.get("query"),
                    genre=arguments.get("genre"),
                    min_rating=arguments.get("min_rating")
                )

            elif tool_name == "get_showtimes":
                result = MovieService.get_showtimes(
                    movie_id=arguments.get("movie_id"),
                    date=arguments.get("date")
                )

            elif tool_name == "get_seat_map":
                seat_map = MovieService.get_seat_map(arguments.get("showtime_id"))
                result = seat_map.model_dump() if seat_map else {"error": "Showtime not found"}

            elif tool_name == "recommend_seats":
                showtime_id = arguments.get("showtime_id")
                count = int(arguments.get("count", 2))
                preferred_tier = arguments.get("preferred_tier")
                seat_map = MovieService.get_seat_map(showtime_id)
                if not seat_map:
                    result = {"error": "Showtime not found"}
                else:
                    # Filter available seats
                    avail = [s for s in seat_map.seats if s.status == "available"]
                    if preferred_tier:
                        tier_matched = [s for s in avail if s.tier.lower() == preferred_tier.lower()]
                        if len(tier_matched) >= count:
                            avail = tier_matched

                    # Find best adjacent seats in the same row
                    rows_grouped: Dict[str, List[Any]] = {}
                    for s in avail:
                        rows_grouped.setdefault(s.row, []).append(s)

                    chosen = []
                    # Check row by row for contiguous numbers
                    for row, r_seats in sorted(rows_grouped.items()):
                        r_seats.sort(key=lambda x: x.number)
                        for i in range(len(r_seats) - count + 1):
                            window = r_seats[i:i+count]
                            # check contiguity
                            is_adjacent = all(window[j+1].number == window[j].number + 1 for j in range(count - 1))
                            if is_adjacent:
                                chosen = [s.id for s in window]
                                break
                        if chosen:
                            break

                    if not chosen and len(avail) >= count:
                        chosen = [s.id for s in avail[:count]]

                    result = {
                        "showtime_id": showtime_id,
                        "movie_title": seat_map.movie_title,
                        "recommended_seat_ids": chosen,
                        "total_available_in_hall": seat_map.total_available
                    }

            elif tool_name == "hold_seats":
                result = BookingService.hold_seats(
                    showtime_id=arguments.get("showtime_id"),
                    seat_ids=arguments.get("seat_ids", []),
                    customer_name=arguments.get("customer_name", "Guest")
                )

            elif tool_name == "apply_promo_code":
                result = BookingService.calculate_pricing(
                    showtime_id=arguments.get("showtime_id"),
                    seat_ids=arguments.get("seat_ids", []),
                    promo_code=arguments.get("promo_code")
                )

            elif tool_name == "confirm_booking":
                req = BookingRequest(
                    showtime_id=arguments.get("showtime_id"),
                    seat_ids=arguments.get("seat_ids", []),
                    customer_name=arguments.get("customer_name") or "Guest Cinephile",
                    customer_email=arguments.get("customer_email") or "guest@cinema.com",
                    promo_code=arguments.get("promo_code"),
                    payment_method=arguments.get("payment_method") or "Credit Card"
                )
                res = BookingService.confirm_booking(req)
                if res.get("success") and "booking" in res:
                    result = {
                        "success": True,
                        "booking": res["booking"].model_dump()
                    }
                else:
                    result = res

            elif tool_name == "lookup_booking":
                booking = BookingService.get_booking(arguments.get("booking_id"))
                result = booking.model_dump() if booking else {"error": "Booking not found"}

            elif tool_name == "cancel_booking":
                result = BookingService.cancel_booking(arguments.get("booking_id"))

            elif tool_name == "recommend_movies":
                result = MovieService.recommend_movies(
                    mood=arguments.get("mood", "mind-bending"),
                    preferences=arguments.get("preferences")
                )

            else:
                result = {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            result = {"error": str(e)}

        exec_time = round((time.time() - start_time) * 1000, 2)
        return ToolCallRecord(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            execution_time_ms=exec_time
        )
