# // Imports
import os
import tempfile
import unittest
from datetime import datetime, date, timedelta
from core.database import (
    init_db,
    create_session,
    close_session,
    get_sessions_for_date
)
from core.engine import (
    get_trends_metrics,
    get_projects_summary,
    get_project_detail,
    get_daily_metrics
)

# // Multi-Day Trend Tests
class TestMultiDayTrends(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "multi_day_test.db")
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_multi_day_evolution_and_projects(self):
        today = date.today()
        d1 = (today - timedelta(days=2))
        d2 = (today - timedelta(days=1))
        d3 = today

        # // Day 1: Coding 2h (LogMorph), Browser 1h
        t1_start = datetime.combine(d1, datetime.min.time()) + timedelta(hours=9)
        s1 = create_session("VS Code", "main.py", "Coding", t1_start, project_context="LogMorph", db_path=self.db_path)
        close_session(s1, t1_start + timedelta(hours=2), 7200, min_duration=1, db_path=self.db_path)

        t1_b = t1_start + timedelta(hours=2)
        s2 = create_session("Firefox", "docs.rs", "Browser", t1_b, project_context="LogMorph", db_path=self.db_path)
        close_session(s2, t1_b + timedelta(hours=1), 3600, min_duration=1, db_path=self.db_path)

        # // Day 2: Coding 4h (LogMorph 3h, FocusShell 1h), Gaming 2h
        t2_start = datetime.combine(d2, datetime.min.time()) + timedelta(hours=10)
        s3 = create_session("VS Code", "tracker.py", "Coding", t2_start, project_context="LogMorph", db_path=self.db_path)
        close_session(s3, t2_start + timedelta(hours=3), 10800, min_duration=1, db_path=self.db_path)

        t2_f = t2_start + timedelta(hours=3)
        s4 = create_session("VS Code", "engine.py", "Coding", t2_f, project_context="FocusShell", db_path=self.db_path)
        close_session(s4, t2_f + timedelta(hours=1), 3600, min_duration=1, db_path=self.db_path)

        t2_g = t2_f + timedelta(hours=1)
        s5 = create_session("Minecraft", "Game", "Gaming", t2_g, project_context="", db_path=self.db_path)
        close_session(s5, t2_g + timedelta(hours=2), 7200, min_duration=1, db_path=self.db_path)

        # // Day 3 (Today): Coding 1h (FocusShell), Terminal 2h (FocusShell)
        t3_start = datetime.combine(d3, datetime.min.time()) + timedelta(hours=8)
        s6 = create_session("VS Code", "views.py", "Coding", t3_start, project_context="FocusShell", db_path=self.db_path)
        close_session(s6, t3_start + timedelta(hours=1), 3600, min_duration=1, db_path=self.db_path)

        t3_t = t3_start + timedelta(hours=1)
        s7 = create_session("Terminal", "bash", "Terminal", t3_t, project_context="FocusShell", db_path=self.db_path)
        close_session(s7, t3_t + timedelta(hours=2), 7200, min_duration=1, db_path=self.db_path)

        # // 1. Verify Trends Metrics
        trends = get_trends_metrics(days_count=7, db_path=self.db_path)
        self.assertEqual(trends["today_duration"], 10800) # 3h
        self.assertEqual(trends["yesterday_duration"], 21600) # 6h
        self.assertEqual(trends["diff_seconds"], 10800 - 21600) # -3h

        # // 2. Verify Projects Summary
        projects = get_projects_summary(db_path=self.db_path)
        p_names = [p["project_name"] for p in projects]
        self.assertIn("LogMorph", p_names)
        self.assertIn("FocusShell", p_names)

        # // LogMorph total = 7200 + 3600 + 10800 = 21600 (6h)
        logmorph = next(p for p in projects if p["project_name"] == "LogMorph")
        self.assertEqual(logmorph["total_duration"], 21600)
        self.assertEqual(logmorph["active_days_count"], 2)

        # // FocusShell total = 3600 + 3600 + 7200 = 14400 (4h)
        focusshell = next(p for p in projects if p["project_name"] == "FocusShell")
        self.assertEqual(focusshell["total_duration"], 14400)
        self.assertEqual(focusshell["active_days_count"], 2)

        # // 3. Verify Project Detail View
        detail = get_project_detail("FocusShell", db_path=self.db_path)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["total_duration"], 14400)
        self.assertEqual(len(detail["applications"]), 2) # VS Code and Terminal

        # // 4. Verify Daily Metrics & Report
        d3_str = d3.strftime("%Y-%m-%d")
        daily = get_daily_metrics(d3_str, db_path=self.db_path)
        self.assertEqual(daily["total_duration"], 10800)
        self.assertEqual(len(daily["projects"]), 1)
        self.assertEqual(daily["projects"][0]["project_name"], "FocusShell")

# // Test Runner
if __name__ == "__main__":
    unittest.main()
