# // Imports
import unittest
from core.context import extract_project_and_context, extract_project_context, is_file_name
from core.naming import normalize_app_name

# // Project Context Unit Tests
class TestProjectContext(unittest.TestCase):
    def test_vscode_titles(self):
        proj, file_ctx = extract_project_and_context("Code", "main.py - FocusShell - Visual Studio Code")
        self.assertEqual(proj, "FocusShell")
        self.assertEqual(file_ctx, "main.py")

        proj, file_ctx = extract_project_and_context("code", "● tracker.py - LogMorph - Visual Studio Code")
        self.assertEqual(proj, "LogMorph")
        self.assertEqual(file_ctx, "tracker.py")

        proj, file_ctx = extract_project_and_context("Antigravity IDE", "WorkSpace - Visual Studio Code - categories.py")
        self.assertEqual(proj, "FocusShell")
        self.assertEqual(file_ctx, "categories.py")

    def test_git_root_primary_identity_regressions(self):
        cases = [
            ("Antigravity", "WorkSpace - Visual Studio Code - tracker.py", "FocusShell", "tracker.py"),
            ("Antigravity", "WorkSpace - Visual Studio Code - README.md", "FocusShell", "README.md"),
            ("Antigravity", "WorkSpace - Visual Studio Code - focusshell", "FocusShell", "focusshell"),
            ("Antigravity", "WorkSpace - Visual Studio Code - context.py", "FocusShell", "context.py"),
            ("Antigravity", "WorkSpace - Visual Studio Code - .gitignore", "FocusShell", ".gitignore"),
            ("Antigravity", "WorkSpace - Visual Studio Code - main.py", "FocusShell", "main.py"),
            ("Antigravity", "WorkSpace - Visual Studio Code - database.py", "FocusShell", "database.py"),
        ]
        for app, raw_title, expected_proj, expected_file in cases:
            proj, file_ctx = extract_project_and_context(app, raw_title)
            self.assertEqual(proj, expected_proj, f"Failed project resolution for title: {raw_title}")
            self.assertEqual(file_ctx, expected_file, f"Failed file context extraction for title: {raw_title}")

    def test_never_classify_filenames_or_workspace_as_projects(self):
        forbidden_candidates = ["README.md", "main.py", "tracker.py", "focusshell", "WorkSpace"]
        for f in forbidden_candidates:
            if is_file_name(f):
                self.assertTrue(is_file_name(f))

    def test_zed_titles(self):
        proj, file_ctx = extract_project_and_context("dev.zed.Zed", "FocusShell — core/tracker.py")
        self.assertEqual(proj, "FocusShell")
        self.assertEqual(file_ctx, "core/tracker.py")

        proj, file_ctx = extract_project_and_context("dev.zed.Zed", "WorkSpace — main.py")
        self.assertEqual(proj, "FocusShell")
        self.assertEqual(file_ctx, "main.py")

    def test_jetbrains_titles(self):
        proj, file_ctx = extract_project_and_context("pycharm", "FocusShell – main.py [FocusShell]")
        self.assertEqual(proj, "FocusShell")
        self.assertEqual(file_ctx, "main.py")

    def test_terminal_titles(self):
        proj, file_ctx = extract_project_and_context("alacritty", "developer@linux: ~/Desktop/Worker/WorkSpace/FocusShell")
        self.assertEqual(proj, "FocusShell")

    def test_browser_page_does_not_become_project(self):
        cases = [
            ("Brave", "FocusShell Roadmap Discussion - Brave", "", "FocusShell Roadmap Discussion"),
            ("Brave", "FocusShell - ChatGPT - Brave", "", "FocusShell"),
            ("Google Chrome", "Google Search - FocusShell tips", "", "Google Search"),
            ("Firefox", "What is Odoo Developer - Firefox", "", "What is Odoo Developer"),
            ("Brave", "New Tab", "", "New Tab")
        ]
        for app, raw_title, expected_proj, expected_ctx in cases:
            proj, ctx = extract_project_and_context(app, raw_title)
            self.assertEqual(proj, expected_proj, f"Browser title '{raw_title}' should not have project '{proj}'")
            self.assertEqual(ctx, expected_ctx, f"Browser context mismatch for '{raw_title}'")

    def test_browser_github_becomes_project(self):
        proj, ctx = extract_project_and_context("Brave", "FocusShell: Terminal Activity Tracker - GitHub")
        self.assertEqual(proj, "FocusShell")
        self.assertEqual(ctx, "GitHub: FocusShell")

    def test_app_normalization(self):
        self.assertEqual(normalize_app_name("dev.zed.Zed"), "Zed")
        self.assertEqual(normalize_app_name("gnome-terminal-server"), "GNOME Terminal")
        self.assertEqual(normalize_app_name("gnome-terminal"), "GNOME Terminal")
        self.assertEqual(normalize_app_name("gnome-system-monitor"), "GNOME System Monitor")
        self.assertEqual(normalize_app_name("brave-browser"), "Brave")
        self.assertEqual(normalize_app_name("google-chrome"), "Google Chrome")
        self.assertEqual(normalize_app_name("Antigravity IDE"), "Antigravity")

# // Test Runner
if __name__ == "__main__":
    unittest.main()
