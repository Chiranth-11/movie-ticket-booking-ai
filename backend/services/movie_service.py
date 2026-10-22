import json
from typing import List, Dict, Any, Optional
from ..database import get_connection
from ..models import Movie, Showtime, Seat, SeatMapResponse

class MovieService:
    @staticmethod
    def list_movies(query: Optional[str] = None, genre: Optional[str] = None, min_rating: Optional[float] = None) -> List[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM movies WHERE 1=1"
        params = []

        if query:
            sql += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(director) LIKE ?)"
            q_wild = f"%{query.lower()}%"
            params.extend([q_wild, q_wild, q_wild])

        if genre:
            sql += " AND LOWER(genre) LIKE ?"
            params.append(f"%{genre.lower()}%")

        if min_rating is not None:
            sql += " AND rating >= ?"
            params.append(min_rating)

        sql += " ORDER BY rating DESC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        movies = []
        for r in rows:
            m = dict(r)
            m["genre"] = json.loads(m["genre"])
            m["cast"] = json.loads(m["cast"])
            movies.append(m)
        return movies

    @staticmethod
    def get_movie(movie_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies WHERE id = ? OR LOWER(title) = ?", (movie_id, movie_id.lower()))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        m = dict(row)
        m["genre"] = json.loads(m["genre"])
        m["cast"] = json.loads(m["cast"])
        return m

    @staticmethod
    def get_showtimes(movie_id: Optional[str] = None, date: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
        SELECT s.*, m.title as movie_title, m.poster_url, m.duration_mins, m.rating
        FROM showtimes s
        JOIN movies m ON s.movie_id = m.id
        WHERE 1=1
        """
        params = []
        if movie_id:
            # Can be id or title match
            if movie_id.startswith("mov-"):
                sql += " AND s.movie_id = ?"
                params.append(movie_id)
            else:
                sql += " AND (s.movie_id = ? OR LOWER(m.title) LIKE ?)"
                params.extend([movie_id, f"%{movie_id.lower()}%"])

        if date:
            sql += " AND s.date = ?"
            params.append(date)

        sql += " ORDER BY s.date ASC, s.time_slot ASC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_seat_map(showtime_id: str) -> Optional[SeatMapResponse]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT s.*, m.title as movie_title, m.id as m_id
        FROM showtimes s
        JOIN movies m ON s.movie_id = m.id
        WHERE s.id = ?
        """, (showtime_id,))
        sh_row = cursor.fetchone()
        if not sh_row:
            conn.close()
            return None

        cursor.execute("""
        SELECT * FROM seats WHERE showtime_id = ? ORDER BY row ASC, number ASC
        """, (showtime_id,))
        seat_rows = cursor.fetchall()
        conn.close()

        seats = []
        available_count = 0
        for sr in seat_rows:
            st = dict(sr)
            seats.append(Seat(
                id=st["seat_id"],
                row=st["row"],
                number=st["number"],
                tier=st["tier"],
                price=st["price"],
                status=st["status"]
            ))
            if st["status"] == "available":
                available_count += 1

        return SeatMapResponse(
            showtime_id=sh_row["id"],
            movie_id=sh_row["m_id"],
            movie_title=sh_row["movie_title"],
            theater_name=sh_row["theater_name"],
            screen_type=sh_row["screen_type"],
            date=sh_row["date"],
            time_slot=sh_row["time_slot"],
            seats=seats,
            total_available=available_count,
            total_seats=len(seats)
        )

    @staticmethod
    def recommend_movies(mood: str, preferences: Optional[str] = None) -> List[Dict[str, Any]]:
        # Intelligent mood-to-genre heuristic mapping
        mood_lower = (mood + " " + (preferences or "")).lower()
        matched_genres = []
        if any(w in mood_lower for w in ["mind-bending", "dream", "space", "future", "sci-fi", "science", "time"]):
            matched_genres.extend(["Sci-Fi", "Adventure"])
        if any(w in mood_lower for w in ["intense", "dark", "batman", "action", "fight", "crime", "thrill"]):
            matched_genres.extend(["Action", "Crime", "Thriller"])
        if any(w in mood_lower for w in ["thoughtful", "history", "physics", "drama", "serious", "atomic"]):
            matched_genres.extend(["Biography", "Drama", "History"])
        if any(w in mood_lower for w in ["calm", "relax", "family", "magic", "spirit", "anime", "beautiful", "kids"]):
            matched_genres.extend(["Animation", "Fantasy", "Family"])

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies ORDER BY rating DESC")
        all_movies = [dict(r) for r in cursor.fetchall()]
        conn.close()

        ranked = []
        for m in all_movies:
            genres = json.loads(m["genre"])
            m["genre"] = genres
            m["cast"] = json.loads(m["cast"])
            score = m["rating"]
            match_count = sum(1 for g in genres if g in matched_genres)
            if match_count > 0:
                score += (match_count * 2.0)
            ranked.append((score, m))

        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in ranked[:3]]
