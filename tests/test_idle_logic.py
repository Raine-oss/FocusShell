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
    get_sessions_for_date
)

# // Idle Logic Tests
class TestIdleLogic(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "idle_test.db")
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_idle_exclusion(self):
        start_time = datetime(2026, 9, 27, 10, 0, 0)
        idle_threshold_seconds = 180
        
        # // User worked 10:00 -> 10:10 (600s active)
        s_id = create_session("VS Code", "main.py", "Coding", start_time, "FocusShell", self.db_path)
        active_duration = 600
        
        # // User is idle from 10:10 to 10:20 (idle reaches threshold at 10:13)
        # // Idle time (10:13 -> 10:20) is frozen, session duration remains 600s
        update_session(s_id, start_time + timedelta(seconds=active_duration), active_duration, self.db_path)
        
        # // User returns at 10:20 and works another 5 minutes (300s)
        new_total_duration = active_duration + 300
        final_end = start_time + timedelta(minutes=25)
        close_session(s_id, final_end, new_total_duration, min_duration=1, db_path=self.db_path)
        
        sessions = get_sessions_for_date("2026-09-27", self.db_path)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["duration_seconds"], 900) # 15 mins active, excluding the 10 min idle

# // Test Runner
if __name__ == "__main__":
    unittest.main()
