# // Imports
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from core.database import (
    init_db,
    create_session,
    update_session,
    close_session,
    get_sessions_for_date,
    get_all_sessions
)
from core.engine import get_daily_metrics

# // Tracker Scenarios Test
class TestTrackerScenarios(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "scenario_test.db")
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_window_switching_sequence(self):
        base_time = datetime(2026, 9, 27, 10, 0, 0)
        
        # // 1. Focus VS Code for 10 minutes
        s1_id = create_session("VS Code", "main.py", "Coding", base_time, project_context="FocusShell", db_path=self.db_path)
        t1_end = base_time + timedelta(minutes=10)
        close_session(s1_id, t1_end, 600, min_duration=1, db_path=self.db_path)

        # // 2. Switch to Firefox for 5 minutes
        s2_id = create_session("Firefox", "GitHub", "Browser", t1_end, project_context="FocusShell", db_path=self.db_path)
        t2_end = t1_end + timedelta(minutes=5)
        close_session(s2_id, t2_end, 300, min_duration=1, db_path=self.db_path)

        # // 3. Switch to Terminal for 3 minutes
        s3_id = create_session("Terminal", "bash", "Terminal", t2_end, project_context="", db_path=self.db_path)
        t3_end = t2_end + timedelta(minutes=3)
        close_session(s3_id, t3_end, 180, min_duration=1, db_path=self.db_path)

        # // 4. Switch back to Firefox for 7 minutes
        s4_id = create_session("Firefox", "StackOverflow", "Browser", t3_end, project_context="", db_path=self.db_path)
        t4_end = t3_end + timedelta(minutes=7)
        close_session(s4_id, t4_end, 420, min_duration=1, db_path=self.db_path)

        # // Assertions
        sessions = get_sessions_for_date("2026-09-27", db_path=self.db_path)
        self.assertEqual(len(sessions), 4)

        for i in range(len(sessions) - 1):
            curr_end = datetime.strptime(sessions[i]["ended_at"], "%Y-%m-%d %H:%M:%S")
            next_start = datetime.strptime(sessions[i+1]["started_at"], "%Y-%m-%d %H:%M:%S")
            self.assertGreaterEqual(next_start, curr_end)

        metrics = get_daily_metrics("2026-09-27", db_path=self.db_path)
        self.assertEqual(metrics["total_duration"], 600 + 300 + 180 + 420)

    def test_file_switching_same_app_does_not_increment_app_opens(self):
        base_time = datetime(2026, 9, 27, 11, 0, 0)
        
        s1 = create_session("Antigravity", "context.py", "Coding", base_time, "FocusShell", self.db_path)
        t1 = base_time + timedelta(minutes=2)
        close_session(s1, t1, 120, min_duration=1, db_path=self.db_path)

        s2 = create_session("Antigravity", "engine.py", "Coding", t1, "FocusShell", self.db_path)
        t2 = t1 + timedelta(minutes=3)
        close_session(s2, t2, 180, min_duration=1, db_path=self.db_path)

        s3 = create_session("Antigravity", "database.py", "Coding", t2, "FocusShell", self.db_path)
        t3 = t2 + timedelta(minutes=1)
        close_session(s3, t3, 60, min_duration=1, db_path=self.db_path)

        metrics = get_daily_metrics("2026-09-27", db_path=self.db_path)
        antigravity_app = next(a for a in metrics["apps"] if a["app_name"] == "Antigravity")
        self.assertEqual(antigravity_app["sessions_count"], 1)

    def test_app_switching_increments_app_opens(self):
        base_time = datetime(2026, 9, 27, 12, 0, 0)
        
        s1 = create_session("Antigravity", "context.py", "Coding", base_time, "FocusShell", self.db_path)
        t1 = base_time + timedelta(minutes=2)
        close_session(s1, t1, 120, min_duration=1, db_path=self.db_path)

        s2 = create_session("GNOME Terminal", "bash", "Terminal", t1, "FocusShell", self.db_path)
        t2 = t1 + timedelta(minutes=1)
        close_session(s2, t2, 60, min_duration=1, db_path=self.db_path)

        s3 = create_session("Antigravity", "context.py", "Coding", t2, "FocusShell", self.db_path)
        t3 = t2 + timedelta(minutes=2)
        close_session(s3, t3, 120, min_duration=1, db_path=self.db_path)

        metrics = get_daily_metrics("2026-09-27", db_path=self.db_path)
        antigravity_app = next(a for a in metrics["apps"] if a["app_name"] == "Antigravity")
        self.assertEqual(antigravity_app["sessions_count"], 2)

    def test_repeated_sampling_extends_same_session(self):
        base_time = datetime(2026, 9, 27, 13, 0, 0)
        
        s_id = create_session("Antigravity", "context.py", "Coding", base_time, "FocusShell", self.db_path)
        update_session(s_id, base_time + timedelta(seconds=2), 2, db_path=self.db_path)
        update_session(s_id, base_time + timedelta(seconds=4), 4, db_path=self.db_path)
        update_session(s_id, base_time + timedelta(seconds=6), 6, db_path=self.db_path)
        close_session(s_id, base_time + timedelta(seconds=6), 6, min_duration=1, db_path=self.db_path)

        sessions = get_sessions_for_date("2026-09-27", db_path=self.db_path)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["duration_seconds"], 6)

    def test_unattributed_excluded_from_real_projects_count(self):
        base_time = datetime(2026, 9, 27, 14, 0, 0)
        
        s1 = create_session("Antigravity", "context.py", "Coding", base_time, "FocusShell", self.db_path)
        t1 = base_time + timedelta(minutes=5)
        close_session(s1, t1, 300, min_duration=1, db_path=self.db_path)

        s2 = create_session("Brave", "ChatGPT", "Browser", t1, "", self.db_path)
        t2 = t1 + timedelta(minutes=5)
        close_session(s2, t2, 300, min_duration=1, db_path=self.db_path)

        metrics = get_daily_metrics("2026-09-27", db_path=self.db_path)
        real_projects = [p for p in metrics["projects"] if p["project_name"] != "Unattributed"]
        self.assertEqual(len(real_projects), 1)
        self.assertEqual(real_projects[0]["project_name"], "FocusShell")

# // Test Runner
if __name__ == "__main__":
    unittest.main()
