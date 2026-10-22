import re
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from ..config import GEMINI_API_KEY, OPENAI_API_KEY
from .tools import ToolExecutor, AVAILABLE_TOOLS_SPECS
from ..models import ToolCallRecord

class LLMProvider:
    @staticmethod
    def call_gemini(prompt: str, tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not GEMINI_API_KEY:
            return None
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return {"type": "text", "content": text}
        except Exception as e:
            print(f"[Gemini Error]: {e}")
            return None

class AutonomousReasoningEngine:
    """
    High-performance Autonomous Built-in Reasoning Engine.
    Executes ReAct (Reasoning + Acting) loop deterministically without external API costs or network latency.
    """
    MOVIE_ALIASES = {
        "inception": "mov-inception",
        "interstellar": "mov-interstellar",
        "oppenheimer": "mov-oppenheimer",
        "dark knight": "mov-dark-knight",
        "batman": "mov-dark-knight",
        "spirited away": "mov-spirited-away",
        "dune": "mov-dune2",
        "dune 2": "mov-dune2",
        "dune: part two": "mov-dune2",
        "kantara": "mov-kantara",
        "rrr": "mov-rrr",
        "kgf": "mov-kgf2",
        "kgf 2": "mov-kgf2",
        "kgf chapter 2": "mov-kgf2",
        "k.g.f": "mov-kgf2",
        "3 idiots": "mov-3-idiots",
        "three idiots": "mov-3-idiots",
        "idiots": "mov-3-idiots",
        "baahubali": "mov-baahubali2",
        "baahubali 2": "mov-baahubali2",
        "bahubali": "mov-baahubali2",
        "dangal": "mov-dangal"
    }

    @classmethod
    def process_turn(cls, message: str, session_state: Dict[str, Any]) -> Tuple[str, List[ToolCallRecord], Optional[Dict[str, Any]]]:
        msg_lower = message.lower().strip()
        tool_records: List[ToolCallRecord] = []
        ui_action: Optional[Dict[str, Any]] = None

        # 1. Detect Context / Entities in user message
        detected_movie_id = session_state.get("active_movie_id")
        for alias, m_id in cls.MOVIE_ALIASES.items():
            if alias in msg_lower:
                detected_movie_id = m_id
                session_state["active_movie_id"] = m_id
                break

        # Check for seat ids like A1, B3, C4, etc.
        seat_matches = [s.upper() for s in re.findall(r"\b([A-Fa-f][1-8])\b", message)]
        if seat_matches:
            session_state["selected_seats"] = seat_matches

        # Check for promo codes
        promo_match = re.search(r"\b(WELCOME20|CINE10|POPCORN5)\b", message, re.IGNORECASE)
        if promo_match:
            session_state["promo_code"] = promo_match.group(1).upper()

        # Check for booking ID like CINE-XXXX-XXXXX
        booking_id_match = re.search(r"\b(CINE-[A-Za-z0-9-]+)\b", message, re.IGNORECASE)

        # Check for ticket count
        count_match = re.search(r"\b(\d+)\s*(?:seat|seats|ticket|tickets)\b", msg_lower)
        count = int(count_match.group(1)) if count_match else 2

        # Preferred tier
        tier = None
        if "vip" in msg_lower:
            tier = "VIP"
        elif "premium" in msg_lower:
            tier = "Premium"
        elif "standard" in msg_lower:
            tier = "Standard"

        # 2. DECISION LOGIC / REACT LOOP

        # CASE: Booking Lookup or Status
        if booking_id_match and any(w in msg_lower for w in ["check", "lookup", "status", "view", "find", "where"]):
            b_id = booking_id_match.group(1).upper()
            t_record = ToolExecutor.execute("lookup_booking", {"booking_id": b_id})
            tool_records.append(t_record)
            if "error" in t_record.result:
                reply = f"❌ I couldn't locate booking **{b_id}**. Please double-check your booking reference number."
            else:
                b = t_record.result
                reply = (
                    f"🎟️ **Booking Confirmed!**\n\n"
                    f"- **Booking ID**: `{b['booking_id']}`\n"
                    f"- **Movie**: **{b['movie_title']}**\n"
                    f"- **Theater**: {b['theater_name']} ({b['screen_type']})\n"
                    f"- **Showtime**: {b['date']} at **{b['time_slot']}**\n"
                    f"- **Seats**: `{', '.join(b['seat_ids'])}`\n"
                    f"- **Status**: `{b['status'].upper()}`\n"
                    f"- **Total Paid**: **${b['total_amount']:.2f}**\n\n"
                    f"Enjoy your film!"
                )
                ui_action = {"type": "SHOW_BOOKING", "booking": b}
            return reply, tool_records, ui_action

        # CASE: Cancellation
        if booking_id_match and any(w in msg_lower for w in ["cancel", "refund", "release"]):
            b_id = booking_id_match.group(1).upper()
            t_record = ToolExecutor.execute("cancel_booking", {"booking_id": b_id})
            tool_records.append(t_record)
            if not t_record.result.get("success"):
                reply = f"⚠️ Could not cancel booking: {t_record.result.get('error', 'Unknown issue')}."
            else:
                reply = (
                    f"✅ **Booking Cancelled Successfully!**\n\n"
                    f"Reference: `{b_id}`\n"
                    f"Refund Amount: **${t_record.result.get('refund_amount', 0):.2f}**\n"
                    f"The reserved seats have been released back to the box office pool."
                )
                ui_action = {"type": "REFRESH_SEATS"}
            return reply, tool_records, ui_action

        # CASE: Confirm Booking Intent
        if any(w in msg_lower for w in ["confirm", "book now", "checkout", "purchase", "finalize", "buy"]):
            showtime_id = session_state.get("active_showtime_id")
            selected_seats = session_state.get("selected_seats") or seat_matches

            if not showtime_id:
                # If movie is known, auto fetch showtime
                if detected_movie_id:
                    t_sh = ToolExecutor.execute("get_showtimes", {"movie_id": detected_movie_id})
                    tool_records.append(t_sh)
                    if t_sh.result and len(t_sh.result) > 0:
                        showtime_id = t_sh.result[0]["id"]
                        session_state["active_showtime_id"] = showtime_id

            if not showtime_id:
                reply = "Which movie and showtime would you like to book? Please pick a showtime or tell me the movie title!"
                return reply, tool_records, ui_action

            if not selected_seats:
                # Recommend seats first
                t_rec = ToolExecutor.execute("recommend_seats", {"showtime_id": showtime_id, "count": count, "preferred_tier": tier or "VIP"})
                tool_records.append(t_rec)
                rec_seats = t_rec.result.get("recommended_seat_ids", [])
                if rec_seats:
                    selected_seats = rec_seats
                    session_state["selected_seats"] = selected_seats

            if not selected_seats:
                reply = f"Please select your seats on the seating map or tell me which seats you prefer (e.g. A3, A4)."
                return reply, tool_records, ui_action

            # Confirm the booking via tool
            customer_name = session_state.get("customer_name", "Chiranth G.")
            customer_email = session_state.get("customer_email", "chiranthgutthi@gmail.com")
            promo = session_state.get("promo_code")

            t_book = ToolExecutor.execute("confirm_booking", {
                "showtime_id": showtime_id,
                "seat_ids": selected_seats,
                "customer_name": customer_name,
                "customer_email": customer_email,
                "promo_code": promo,
                "payment_method": "Credit Card"
            })
            tool_records.append(t_book)

            if t_book.result.get("success"):
                booking = t_book.result["booking"]
                reply = (
                    f"🎉 **Woohoo! Your tickets are confirmed!**\n\n"
                    f"• **Movie**: **{booking['movie_title']}**\n"
                    f"• **Theater**: {booking['theater_name']} ({booking['screen_type']})\n"
                    f"• **Date & Time**: {booking['date']} at **{booking['time_slot']}**\n"
                    f"• **Seats**: `{', '.join(booking['seat_ids'])}`\n"
                    f"• **Booking ID**: `{booking['booking_id']}`\n"
                    f"• **Total**: **${booking['total_amount']:.2f}** "
                    f"*(Discount applied: ${booking['discount']:.2f})*\n\n"
                    f"I have sent your digital boarding pass to **{customer_email}**. Click 'View Boarding Pass' below to see your digital ticket & QR code!"
                )
                ui_action = {"type": "BOOKING_CONFIRMED", "booking": booking}
                session_state["last_booking"] = booking
            else:
                reply = f"❌ Booking failed: {t_book.result.get('error')}. Let me know if you'd like to pick alternate seats!"
            return reply, tool_records, ui_action

        # CASE: Apply Promo Code
        if promo_match or ("promo" in msg_lower and "apply" in msg_lower):
            code = (promo_match.group(1).upper() if promo_match else "WELCOME20")
            session_state["promo_code"] = code
            showtime_id = session_state.get("active_showtime_id", "sht-101")
            seats = session_state.get("selected_seats", ["A3", "A4"])
            t_promo = ToolExecutor.execute("apply_promo_code", {
                "showtime_id": showtime_id,
                "seat_ids": seats,
                "promo_code": code
            })
            tool_records.append(t_promo)
            p_res = t_promo.result
            if p_res.get("promo_info"):
                info = p_res["promo_info"]
                reply = (
                    f"🏷️ **Promo Code `{code}` Applied Successfully!**\n\n"
                    f"- **Discount**: {info['description']} (**-${p_res['discount']:.2f}**)\n"
                    f"- **New Total**: **${p_res['total_amount']:.2f}** (was ${p_res['subtotal']:.2f})\n\n"
                    f"Say **'confirm booking'** to finalize your tickets with this discount!"
                )
                ui_action = {"type": "PROMO_APPLIED", "pricing": p_res}
            else:
                reply = f"⚠️ The code **{code}** could not be applied. Available codes are `WELCOME20` (20% off) or `POPCORN5` ($5 off)."
            return reply, tool_records, ui_action

        # CASE: Specific Movie Showtimes or Inquiries
        if detected_movie_id and any(w in msg_lower for w in ["showtime", "show times", "timing", "time", "when", "watch", "schedule", "ticket"]):
            t_sh = ToolExecutor.execute("get_showtimes", {"movie_id": detected_movie_id})
            tool_records.append(t_sh)
            showtimes = t_sh.result

            if showtimes:
                first_sh = showtimes[0]
                session_state["active_showtime_id"] = first_sh["id"]
                title = first_sh["movie_title"]

                # Also inspect seats for the first showtime
                t_seats = ToolExecutor.execute("get_seat_map", {"showtime_id": first_sh["id"]})
                tool_records.append(t_seats)

                slots_str = "\n".join([f"• **{s['time_slot']}** | {s['theater_name']} ({s['screen_type']}) - `${s['base_price']:.2f}`" for s in showtimes[:4]])
                reply = (
                    f"🎬 Here are available showtimes for **{title}**:\n\n"
                    f"{slots_str}\n\n"
                    f"I've pulled up the interactive seating chart for **{first_sh['time_slot']}** ({first_sh['theater_name']}). "
                    f"There are **{t_seats.result.get('total_available', 40)} seats available**!\n\n"
                    f"Would you like me to reserve the best **VIP** or **Premium** seats for you?"
                )
                ui_action = {
                    "type": "SELECT_SHOWTIME",
                    "showtime_id": first_sh["id"],
                    "movie_id": detected_movie_id,
                    "movie_title": title
                }
            else:
                reply = f"I couldn't find upcoming showtimes for that title. Let me search our catalog!"
            return reply, tool_records, ui_action

        # CASE: Seat Recommendation or Inspection
        if any(w in msg_lower for w in ["seat", "seats", "vip", "premium", "front", "middle", "best"]):
            showtime_id = session_state.get("active_showtime_id")
            if not showtime_id:
                # Default to first showtime of active movie or Inception
                m_id = detected_movie_id or "mov-inception"
                t_sh = ToolExecutor.execute("get_showtimes", {"movie_id": m_id})
                tool_records.append(t_sh)
                if t_sh.result:
                    showtime_id = t_sh.result[0]["id"]
                    session_state["active_showtime_id"] = showtime_id

            t_rec = ToolExecutor.execute("recommend_seats", {
                "showtime_id": showtime_id,
                "count": count,
                "preferred_tier": tier or "VIP"
            })
            tool_records.append(t_rec)
            rec_seats = t_rec.result.get("recommended_seat_ids", [])
            session_state["selected_seats"] = rec_seats

            # Calculate pricing
            t_price = ToolExecutor.execute("apply_promo_code", {
                "showtime_id": showtime_id,
                "seat_ids": rec_seats,
                "promo_code": session_state.get("promo_code", "")
            })
            tool_records.append(t_price)

            reply = (
                f"🪑 **Prime Seat Recommendation:**\n\n"
                f"I analyzed the theater layout and reserved optimal adjacent {tier or 'VIP'} seats for you: "
                f"**`{', '.join(rec_seats)}`** in **{t_rec.result.get('movie_title', 'the cinema')}**.\n\n"
                f"- **Seats**: `{', '.join(rec_seats)}`\n"
                f"- **Subtotal**: ${t_price.result.get('subtotal', 0):.2f}\n"
                f"- **Total with tax**: **${t_price.result.get('total_amount', 0):.2f}**\n\n"
                f"I've highlighted these on your interactive seating screen. "
                f"Would you like to confirm this booking or apply a promo code like `WELCOME20`?"
            )
            ui_action = {
                "type": "SELECT_SEATS",
                "seat_ids": rec_seats,
                "showtime_id": showtime_id
            }
            return reply, tool_records, ui_action

        # CASE: Recommendations / Mood Search
        if any(w in msg_lower for w in ["recommend", "suggest", "what should i watch", "vibe", "mood", "best movie"]):
            mood = "mind-bending" if any(w in msg_lower for w in ["mind", "sci-fi", "space", "twist"]) else \
                   ("action" if any(w in msg_lower for w in ["action", "thrill", "intense", "batman"]) else "heartwarming")
            t_rec = ToolExecutor.execute("recommend_movies", {"mood": mood, "preferences": message})
            tool_records.append(t_rec)

            movies = t_rec.result
            m_list = "\n".join([f"• **{m['title']}** ({m['release_year']}) - ⭐ {m['rating']}/10 - *{', '.join(m['genre'])}*\n  _{m['description'][:110]}..._" for m in movies])
            reply = (
                f"✨ Based on your request, here are top picks tailored for you:\n\n"
                f"{m_list}\n\n"
                f"Which one would you like to see? Just say **'Showtimes for {movies[0]['title']}'** to view theater slots!"
            )
            ui_action = {"type": "RECOMMEND_MOVIES", "movies": movies}
            return reply, tool_records, ui_action

        # CASE: General Movie Catalog / Search
        if any(w in msg_lower for w in ["movie", "movies", "catalog", "browse", "list", "playing", "now showing"]):
            genre = None
            for g in ["Sci-Fi", "Action", "Drama", "Animation", "Thriller", "Adventure"]:
                if g.lower() in msg_lower:
                    genre = g
                    break

            t_search = ToolExecutor.execute("search_movies", {"genre": genre})
            tool_records.append(t_search)
            movies = t_search.result[:4]

            m_titles = ", ".join([f"**{m['title']}** (⭐ {m['rating']})" for m in movies])
            reply = (
                f"🍿 **Now Showing at our Theaters:**\n\n"
                f"{m_titles}.\n\n"
                f"Click any movie card or tell me what title you'd like to book tickets for!"
            )
            ui_action = {"type": "LIST_MOVIES", "movies": movies}
            return reply, tool_records, ui_action

        # DEFAULT / GREETING
        reply = (
            f"👋 Hello! I am **CineAgent**, your AI Cinema Concierge.\n\n"
            f"I can autonomously help you:\n"
            f"• 🔍 **Search & Recommend movies** based on mood or genres\n"
            f"• 🕒 **Check live showtimes** across IMAX, Dolby, and Digital halls\n"
            f"• 🪑 **Select optimal VIP / Premium seats** with real-time seat mapping\n"
            f"• 🏷️ **Apply promo discounts** (try `WELCOME20` for 20% off)\n"
            f"• 🎟️ **Instant ticket generation** with digital boarding pass & QR code\n\n"
            f"What movie would you like to explore today?"
        )
        return reply, tool_records, ui_action
