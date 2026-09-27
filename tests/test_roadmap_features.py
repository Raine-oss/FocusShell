# // Imports
import os
import tempfile
import unittest
from datetime import datetime, date

from core.database import (
    init_db,
    create_session,
    close_session,
    set_goal,
    get_goals,
    delete_goal
)
from core.engine import (
    parse_duration_string,
    format_seconds,
    get_insights_metrics,
    get_goals_progress,
    get_project_detail,
    analyze_timeline_transitions
)

# // Test Roadmap Features
class TestRoadmapFeatures(unittest.TestCase):
    
    # // Setup & Teardown
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_roadmap.db")
        init_db(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    # // Duration Parsing Tests
    def test_parse_duration_string(self):
        self.assertEqual(parse_duration_string("45m"), 2700)
        self.assertEqual(parse_duration_string("2h"), 7200)
        self.assertEqual(parse_duration_string("1h30m"), 5400)
        self.assertEqual(parse_duration_string("90s"), 90)
        self.assertEqual(parse_duration_string("30"), 1800)
        self.assertEqual(parse_duration_string(""), 0)

    # // Goals Storage & Progress Tests
    def test_goals_crud_and_progress(self):
        today_str = date.today().strftime("%Y-%m-%d")
        
        # Add goal
        set_goal("FocusShell", 3600, target_type="project", db_path=self.db_path)
        goals = get_goals(db_path=self.db_path)
        self.assertEqual(len(goals), 1)
        self.assertEqual(goals[0]["target_name"], "FocusShell")
        self.assertEqual(goals[0]["target_seconds"], 3600)
        
        # Add a session matching goal
        s_id = create_session(
            "Antigravity", "main.py", "Coding",
            datetime.strptime(f"{today_str} 10:00:00", "%Y-%m-%d %H:%M:%S"),
            project_context="FocusShell",
            db_path=self.db_path
        )
        close_session(s_id, datetime.strptime(f"{today_str} 10:30:00", "%Y-%m-%d %H:%M:%S"), 1800, db_path=self.db_path)
        
        # Check progress
        progress = get_goals_progress(target_date=today_str, db_path=self.db_path)
        self.assertEqual(len(progress), 1)
        g_prog = progress[0]
        self.assertEqual(g_prog["target_name"], "FocusShell")
        self.assertEqual(g_prog["achieved_seconds"], 1800)
        self.assertEqual(g_prog["remaining_seconds"], 1800)
        self.assertAlmostEqual(g_prog["percentage"], 50.0)
        self.assertFalse(g_prog["is_completed"])
        
        # Delete goal
        deleted = delete_goal("FocusShell", db_path=self.db_path)
        self.assertTrue(deleted)
        self.assertEqual(len(get_goals(db_path=self.db_path)), 0)

    # // Insights Engine Tests
    def test_insights_metrics(self):
        today_str = date.today().strftime("%Y-%m-%d")
        
        # Session 1: Focus project
        s1 = create_session(
            "Antigravity", "context.py", "Coding",
            datetime.strptime(f"{today_str} 19:10:00", "%Y-%m-%d %H:%M:%S"),
            project_context="FocusShell",
            db_path=self.db_path
        )
        close_session(s1, datetime.strptime(f"{today_str} 19:22:00", "%Y-%m-%d %H:%M:%S"), 720, db_path=self.db_path)
        
        # Session 2: Distraction
        s2 = create_session(
            "Discord", "Direct Messages", "Social",
            datetime.strptime(f"{today_str} 19:22:00", "%Y-%m-%d %H:%M:%S"),
            project_context="",
            db_path=self.db_path
        )
        close_session(s2, datetime.strptime(f"{today_str} 19:25:00", "%Y-%m-%d %H:%M:%S"), 180, db_path=self.db_path)
        
        insights = get_insights_metrics(target_date=today_str, db_path=self.db_path)
        self.assertEqual(insights["total_duration"], 900)
        self.assertEqual(len(insights["projects"]), 1)
        self.assertEqual(insights["projects"][0]["project_name"], "FocusShell")
        self.assertEqual(insights["projects"][0]["total_duration"], 720)
        
        self.assertEqual(len(insights["distractions"]), 1)
        self.assertEqual(insights["distractions"][0]["name"], "Discord")
        self.assertEqual(insights["distractions"][0]["duration"], 180)
        
        patterns = insights["patterns"]
        self.assertEqual(patterns["most_active_hour"], "19:00–20:00")
        self.assertIsNotNone(patterns["longest_uninterrupted"])
        self.assertEqual(patterns["longest_uninterrupted"]["duration"], 720)

    # // Project Detail Memory Tests
    def test_project_detail_memory(self):
        today_str = date.today().strftime("%Y-%m-%d")
        
        s1 = create_session(
            "Antigravity", "context.py", "Coding",
            datetime.strptime(f"{today_str} 10:00:00", "%Y-%m-%d %H:%M:%S"),
            project_context="FocusShell",
            db_path=self.db_path
        )
        close_session(s1, datetime.strptime(f"{today_str} 10:15:00", "%Y-%m-%d %H:%M:%S"), 900, db_path=self.db_path)
        
        detail = get_project_detail("FocusShell", db_path=self.db_path)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["project_name"], "FocusShell")
        self.assertEqual(detail["total_duration"], 900)
        self.assertEqual(detail["longest_session"], 900)
        self.assertEqual(len(detail["files"]), 1)
        self.assertEqual(detail["files"][0]["window_title"], "context.py")
        self.assertEqual(len(detail["recent_activity"]), 1)
        self.assertEqual(detail["recent_activity"][0]["window_title"], "context.py")

    # // Timeline Transitions Tests
    def test_timeline_transitions(self):
        sessions = [
            {
                "app_name": "Antigravity",
                "project_context": "FocusShell",
                "window_title": "context.py",
                "started_at": "2026-09-27 19:10:00",
                "ended_at": "2026-09-27 19:22:00",
                "duration_seconds": 720
            },
            {
                "app_name": "Antigravity",
                "project_context": "FocusShell",
                "window_title": "engine.py",
                "started_at": "2026-09-27 19:22:00",
                "ended_at": "2026-09-27 19:30:00",
                "duration_seconds": 480
            },
            {
                "app_name": "Brave",
                "project_context": "",
                "window_title": "ChatGPT",
                "started_at": "2026-09-27 19:35:00",
                "ended_at": "2026-09-27 19:38:00",
                "duration_seconds": 180
            }
        ]
        
        analyzed = analyze_timeline_transitions(sessions)
        self.assertEqual(len(analyzed), 3)
        self.assertEqual(analyzed[0]["transition_cause"], "Context switch")
        self.assertTrue("Idle / Break" in analyzed[1]["transition_cause"])
        self.assertEqual(analyzed[2]["transition_cause"], "Active session")

# // Execution
if __name__ == "__main__":
    unittest.main()
