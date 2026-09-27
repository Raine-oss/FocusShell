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
    get_sessions_for_date
)

# // Data Integrity Unit Tests
class TestDataIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "integrity_test.db")
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_negative_duration_prevention(self):
        start = datetime(2026, 9, 27, 10, 0, 0)
        s_id = create_session("TestApp", "TestTitle", "Other", start, "", self.db_path)
        update_session(s_id, start, -50, self.db_path)
        sessions = get_sessions_for_date("2026-09-27", self.db_path)
        self.assertEqual(len(sessions), 0)

    def test_empty_app_name_sanitization(self):
        start = datetime(2026, 9, 27, 10, 0, 0)
        s_id = create_session("   ", "", "", start, "", self.db_path)
        close_session(s_id, start, 100, min_duration=1, db_path=self.db_path)
        
        sessions = get_sessions_for_date("2026-09-27", self.db_path)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["app_name"], "Unknown")
        self.assertEqual(sessions[0]["category"], "Other")

# // Test Runner
if __name__ == "__main__":
    unittest.main()
