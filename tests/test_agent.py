import unittest
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.database import init_db
from backend.agent.tools import ToolExecutor, AVAILABLE_TOOLS_SPECS
from backend.agent.core import CineAgent
from backend.models import ChatRequest

class TestAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_available_tools_registry(self):
        self.assertGreaterEqual(len(AVAILABLE_TOOLS_SPECS), 9)
        tool_names = [t["name"] for t in AVAILABLE_TOOLS_SPECS]
        self.assertIn("search_movies", tool_names)
        self.assertIn("get_showtimes", tool_names)
        self.assertIn("get_seat_map", tool_names)
        self.assertIn("recommend_seats", tool_names)
        self.assertIn("apply_promo_code", tool_names)
        self.assertIn("confirm_booking", tool_names)
        self.assertIn("lookup_booking", tool_names)
        self.assertIn("cancel_booking", tool_names)

    def test_search_movies_tool(self):
        record = ToolExecutor.execute("search_movies", {"query": "Inception"})
        self.assertEqual(record.tool_name, "search_movies")
        self.assertIsInstance(record.result, list)
        self.assertGreaterEqual(len(record.result), 1)
        self.assertEqual(record.result[0]["title"], "Inception")

    def test_get_showtimes_tool(self):
        record = ToolExecutor.execute("get_showtimes", {"movie_id": "mov-inception"})
        self.assertEqual(record.tool_name, "get_showtimes")
        self.assertIsInstance(record.result, list)
        self.assertGreater(len(record.result), 0)
        self.assertEqual(record.result[0]["movie_id"], "mov-inception")

    def test_recommend_seats_tool(self):
        sh_record = ToolExecutor.execute("get_showtimes", {"movie_id": "mov-inception"})
        showtime_id = sh_record.result[0]["id"]

        rec_record = ToolExecutor.execute("recommend_seats", {
            "showtime_id": showtime_id,
            "count": 2,
            "preferred_tier": "VIP"
        })
        self.assertEqual(rec_record.tool_name, "recommend_seats")
        self.assertIn("recommended_seat_ids", rec_record.result)
        self.assertEqual(len(rec_record.result["recommended_seat_ids"]), 2)

    def test_apply_promo_code_tool(self):
        sh_record = ToolExecutor.execute("get_showtimes", {"movie_id": "mov-inception"})
        showtime_id = sh_record.result[0]["id"]

        promo_record = ToolExecutor.execute("apply_promo_code", {
            "showtime_id": showtime_id,
            "seat_ids": ["A3", "A4"],
            "promo_code": "WELCOME20"
        })
        self.assertGreater(promo_record.result["discount"], 0)
        self.assertEqual(promo_record.result["promo_info"]["code"], "WELCOME20")

    def test_cine_agent_chat_turn(self):
        agent = CineAgent()
        req = ChatRequest(message="What showtimes are available for Inception?", session_id="test_session_1")
        resp = agent.chat(req)

        self.assertIsNotNone(resp.reply)
        self.assertGreater(len(resp.tool_calls), 0)
        self.assertEqual(resp.tool_calls[0].tool_name, "get_showtimes")
        self.assertIsNotNone(resp.ui_action)
        self.assertEqual(resp.ui_action["type"], "SELECT_SHOWTIME")

    def test_indian_movie_chat_and_showtimes(self):
        agent = CineAgent()
        req = ChatRequest(message="What showtimes do you have for Kantara?", session_id="test_kantara_1")
        resp = agent.chat(req)

        self.assertIsNotNone(resp.reply)
        self.assertIn("Kantara", resp.reply)
        self.assertGreater(len(resp.tool_calls), 0)
        self.assertEqual(resp.tool_calls[0].tool_name, "get_showtimes")
        self.assertEqual(resp.ui_action["movie_id"], "mov-kantara")

if __name__ == "__main__":
    unittest.main()
