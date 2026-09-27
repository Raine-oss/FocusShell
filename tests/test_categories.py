# // Imports
import unittest
from core.categories import categorize_window
from core.engine import format_seconds

# // Categories Unit Tests
class TestCategories(unittest.TestCase):
    def test_default_categories(self):
        self.assertEqual(categorize_window("Code", "file.py"), "Coding")
        self.assertEqual(categorize_window("dev.zed.Zed", "main.py"), "Coding")
        self.assertEqual(categorize_window("zed", "tracker.py"), "Coding")
        self.assertEqual(categorize_window("Zed", "FocusShell — file.py"), "Coding")
        self.assertEqual(categorize_window("firefox", "GitHub"), "Browser")
        self.assertEqual(categorize_window("discord", "General"), "Social")
        self.assertEqual(categorize_window("alacritty", "bash"), "Terminal")
        self.assertEqual(categorize_window("gnome-terminal", "bash"), "Terminal")
        self.assertEqual(categorize_window("spotify", "Song"), "Media")
        self.assertEqual(categorize_window("minecraft", "Game"), "Gaming")
        self.assertEqual(categorize_window("RandomApp", "RandomTitle"), "Other")

    def test_duration_formatter(self):
        self.assertEqual(format_seconds(45), "45s")
        self.assertEqual(format_seconds(120), "2m")
        self.assertEqual(format_seconds(3600), "1h")
        self.assertEqual(format_seconds(3720), "1h 02m")

# // Test Runner
if __name__ == "__main__":
    unittest.main()
