# // Imports
import os
import tempfile
import unittest
from datetime import datetime, date, timedelta

from core.database import init_db, create_session, close_session
from core.review import build_daily_review, resolve_target_date

# // Test Review Engine
class TestReviewEngine(unittest.TestCase):
    
    # // Setup & Teardown
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_review.db")
        init_db(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    # // Date Resolution Tests
    def test_resolve_target_date(self):
        today_str = date.today().strftime("%Y-%m-%d")
        yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        self.assertEqual(resolve_target_date(None), today_str)
        self.assertEqual(resolve_target_date("today"), today_str)
        self.assertEqual(resolve_target_date("yesterday"), yesterday_str)
        self.assertEqual(resolve_target_date("2026-09-20"), "2026-09-20")

    # // Empty Day Review Tests
    def test_empty_day_review(self):
        rev = build_daily_review("2026-01-01", db_path=self.db_path)
        self.assertTrue(rev["is_empty"])
        self.assertEqual(rev["overview"]["active_time"], 0)
        self.assertIsNone(rev["main_project"])
        self.assertEqual(len(rev["highlights"]), 1)

    # // Populated Day Review Tests
    def test_populated_day_review(self):
        today_str = date.today().strftime("%Y-%m-%d")
        
        # Project session
        s1 = create_session(
            "Antigravity", "context.py", "Coding",
            datetime.strptime(f"{today_str} 14:00:00", "%Y-%m-%d %H:%M:%S"),
            project_context="FocusShell",
            db_path=self.db_path
        )
        close_session(s1, datetime.strptime(f"{today_str} 14:30:00", "%Y-%m-%d %H:%M:%S"), 1800, db_path=self.db_path)
        
        # Unattributed browsing session
        s2 = create_session(
            "Brave", "Docs", "Browsing",
            datetime.strptime(f"{today_str} 14:30:00", "%Y-%m-%d %H:%M:%S"),
            project_context="",
            db_path=self.db_path
        )
        close_session(s2, datetime.strptime(f"{today_str} 14:40:00", "%Y-%m-%d %H:%M:%S"), 600, db_path=self.db_path)
        
        rev = build_daily_review(today_str, db_path=self.db_path)
        
        self.assertFalse(rev["is_empty"])
        self.assertEqual(rev["overview"]["active_time"], 2400)
        self.assertEqual(rev["overview"]["project_time"], 1800)
        self.assertEqual(rev["overview"]["unattributed_time"], 600)
        
        self.assertIsNotNone(rev["main_project"])
        self.assertEqual(rev["main_project"]["name"], "FocusShell")
        
        self.assertEqual(len(rev["top_applications"]), 2)
        self.assertEqual(rev["top_applications"][0]["name"], "Antigravity")
        
        # Verify factual non-judgmental highlights
        self.assertTrue(any("FocusShell was your main tracked project" in h for h in rev["highlights"]))
        self.assertTrue(any("Antigravity was your most-used application" in h for h in rev["highlights"]))
        self.assertTrue(any("unattributed to a tracked project" in h for h in rev["highlights"]))

# // Execution
if __name__ == "__main__":
    unittest.main()
