import unittest
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.database import init_db
from backend.models import ChatRequest, BookingRequest
from backend.app import (
    get_movies,
    get_movie_detail,
    get_showtimes,
    get_seat_map,
    get_agent_tools,
    chat_with_agent,
    create_booking
)

class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_get_movies(self):
        movies = get_movies()
        self.assertIsInstance(movies, list)
        self.assertGreaterEqual(len(movies), 5)
        titles = [m["title"] for m in movies]
        self.assertIn("Inception", titles)

    def test_filter_movies_by_genre(self):
        sci_fi_movies = get_movies(genre="Sci-Fi")
        self.assertGreater(len(sci_fi_movies), 0)
        for m in sci_fi_movies:
            self.assertIn("Sci-Fi", m["genre"])

    def test_filter_indian_movies(self):
        indian_movies = get_movies(genre="Indian Cinema")
        self.assertGreaterEqual(len(indian_movies), 6)
        titles = [m["title"] for m in indian_movies]
        self.assertIn("Kantara", titles)
        self.assertIn("RRR", titles)
        self.assertIn("K.G.F: Chapter 2", titles)

    def test_get_movie_detail(self):
        movie = get_movie_detail("mov-inception")
        self.assertEqual(movie["id"], "mov-inception")
        self.assertEqual(movie["title"], "Inception")

    def test_get_showtimes(self):
        showtimes = get_showtimes(movie_id="mov-inception")
        self.assertGreater(len(showtimes), 0)
        self.assertEqual(showtimes[0]["movie_id"], "mov-inception")

    def test_get_seat_map(self):
        showtimes = get_showtimes(movie_id="mov-inception")
        sh_id = showtimes[0]["id"]
        seat_map = get_seat_map(sh_id)
        self.assertEqual(seat_map.showtime_id, sh_id)
        self.assertEqual(len(seat_map.seats), 48)

    def test_get_agent_tools(self):
        tools_info = get_agent_tools()
        self.assertEqual(tools_info["status"], "active")
        self.assertGreaterEqual(tools_info["tools_count"], 9)

    def test_chat_with_agent_endpoint(self):
        req = ChatRequest(message="Recommend 2 VIP seats for Inception", session_id="api_test_session")
        resp = chat_with_agent(req)
        self.assertIsNotNone(resp.reply)
        self.assertGreater(len(resp.tool_calls), 0)
        self.assertEqual(resp.ui_action["type"], "SELECT_SEATS")

if __name__ == "__main__":
    unittest.main()
