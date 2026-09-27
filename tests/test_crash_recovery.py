# // Imports
import os
import tempfile
import unittest
from datetime import datetime
from core.database import (
    init_db,
    create_session,
    update_session,
    recover_stale_sessions,
    get_sessions_for_date
)

# // Crash Recovery Unit Tests
class TestCrashRecovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "crash_test.db")
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_stale_empty_session_cleanup(self):
        start = datetime(2026, 9, 27, 10, 0, 0)
        
        # // Create session that died with 0 duration
        s1_id = create_session("VS Code", "crash.py", "Coding", start, "", self.db_path)
        
        # // Create session that had progress before crash
        s2_id = create_session("Firefox", "docs.rs", "Browser", start, "", self.db_path)
        update_session(s2_id, datetime(2026, 9, 27, 10, 15, 0), 900, self.db_path)
        
        # // Run recovery
        recovered = recover_stale_sessions(self.db_path)
        self.assertGreaterEqual(recovered, 1)
        
        sessions = get_sessions_for_date("2026-09-27", self.db_path)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["app_name"], "Firefox")
        self.assertEqual(sessions[0]["duration_seconds"], 900)

# // Test Runner
if __name__ == "__main__":
    unittest.main()
