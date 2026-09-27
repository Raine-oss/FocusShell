# // Imports
import os
import tempfile
import unittest
from datetime import datetime
from core.database import (
    init_db,
    create_session,
    update_session,
    close_session,
    get_sessions_for_date,
    set_custom_category,
    get_custom_categories
)

# // Database Unit Tests
class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_focus.db")
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_session_lifecycle(self):
        start = datetime(2026, 9, 27, 10, 0, 0)
        end = datetime(2026, 9, 27, 10, 20, 0)
        
        sess_id = create_session("Code", "main.py", "Coding", start, project_context="FocusShell", db_path=self.db_path)
        self.assertIsNotNone(sess_id)
        
        update_session(sess_id, end, 1200, db_path=self.db_path)
        
        sessions = get_sessions_for_date("2026-09-27", db_path=self.db_path)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["app_name"], "VS Code")
        self.assertEqual(sessions[0]["project_context"], "FocusShell")
        self.assertEqual(sessions[0]["duration_seconds"], 1200)

    def test_min_duration_filter(self):
        start = datetime(2026, 9, 27, 11, 0, 0)
        sess_id = create_session("Code", "quick.py", "Coding", start, project_context="", db_path=self.db_path)
        close_session(sess_id, start, 0, min_duration=1, db_path=self.db_path)
        
        sessions = get_sessions_for_date("2026-09-27", db_path=self.db_path)
        self.assertEqual(len(sessions), 0)

    def test_custom_categories(self):
        set_custom_category("figma", "Design", db_path=self.db_path)
        rules = get_custom_categories(db_path=self.db_path)
        self.assertIn("figma", rules)
        self.assertEqual(rules["figma"], "Design")

# // Test Runner
if __name__ == "__main__":
    unittest.main()
