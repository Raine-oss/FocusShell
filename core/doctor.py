# // Imports
import os
import json
import shutil
import sqlite3
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from core.database import get_db_path, get_db_connection, get_all_sessions, get_last_session
from core.tracker import get_active_window
from core.idle import get_idle_seconds
from core.daemon import get_daemon_pid, LOG_FILE
from core.config import DEFAULT_DATA_DIR, load_config
from core.engine import get_current_status_metrics, format_seconds

console = Console()

# // Doctor Diagnostics
def run_diagnostics() -> None:
    console.print()
    console.print(Panel("[bold cyan]FocusShell — System & Environment Doctor[/bold cyan]", box=box.ROUNDED, border_style="cyan"))
    
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column("Component", style="bold white", width=25)
    table.add_column("Status", width=14)
    table.add_column("Details", style="dim", width=45)
    
    # // 1. Display Server Check
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown").lower()
    if session_type in ("x11", "wayland"):
        table.add_row("Display Server", "[bold green]✓ Ready[/bold green]", f"Session Type: {session_type.upper()}")
    else:
        table.add_row("Display Server", "[bold yellow]! Warning[/bold yellow]", f"Unknown XDG_SESSION_TYPE: {session_type}")

    # // 2. Active Window Capture
    app, title = get_active_window()
    if app and title:
        disp = title if len(title) <= 35 else title[:32] + "..."
        table.add_row("Window Capture", "[bold green]✓ Working[/bold green]", f"{app} — {disp}")
    else:
        table.add_row("Window Capture", "[bold yellow]! Idle/None[/bold yellow]", "No active window currently detected")

    # // 3. Idle Detection Check
    idle_sec = get_idle_seconds()
    if idle_sec is not None:
        table.add_row("Idle Detector", "[bold green]✓ Active[/bold green]", f"Current Idle: {int(idle_sec)}s (XScreenSaver / ctypes)")
    else:
        table.add_row("Idle Detector", "[bold yellow]! Fallback[/bold yellow]", "Native idle not supported, using fallback")

    # // 4. SQLite Database Health
    db_path = get_db_path()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        res = cur.fetchone()[0]
        cur.execute("PRAGMA journal_mode;")
        j_mode = cur.fetchone()[0]
        conn.close()
        if res.lower() == "ok":
            table.add_row("Database Integrity", "[bold green]✓ Healthy[/bold green]", f"WAL Mode: {j_mode.upper()} ({os.path.basename(db_path)})")
        else:
            table.add_row("Database Integrity", "[bold red]✗ Corrupt[/bold red]", f"Integrity check failed: {res}")
    except Exception as e:
        table.add_row("Database Integrity", "[bold red]✗ Error[/bold red]", str(e))

    # // 5. Tracker Daemon Status
    pid = get_daemon_pid()
    if pid is not None:
        table.add_row("Tracker Daemon", "[bold green]● Running[/bold green]", f"Process PID: {pid}")
    else:
        table.add_row("Tracker Daemon", "[bold dim]○ Stopped[/bold dim]", "Not running (start with `focusshell start`)")

    # // 6. Session State Consistency
    cache_path = os.path.join(DEFAULT_DATA_DIR, "active_state.json")
    is_state_consistent = True
    state_detail = "Aligned with SQLite"
    if pid is not None:
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    c_data = json.load(f)
                    ts = c_data.get("timestamp")
                    if ts:
                        ts_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                        age = int((datetime.now() - ts_dt).total_seconds())
                        if age > 45:
                            is_state_consistent = False
                            state_detail = f"Cache stale ({age}s old)"
                        else:
                            state_detail = f"Synchronized (PID {pid})"
            except Exception:
                is_state_consistent = False
                state_detail = "Cache read error"
        else:
            is_state_consistent = False
            state_detail = "Active state cache missing"
        
        if is_state_consistent:
            table.add_row("Session State", "[bold green]✓ Consistent[/bold green]", state_detail)
        else:
            table.add_row("Session State", "[bold yellow]! Desync[/bold yellow]", state_detail)
    else:
        table.add_row("Session State", "[bold dim]○ Inactive[/bold dim]", "Daemon stopped")

    # // 7. Active Session Metrics
    status_metrics = get_current_status_metrics()
    live_sec = status_metrics.get("live_session_seconds", 0)
    if pid is not None and live_sec > 0:
        table.add_row("Active Session", "[bold green]✓ Active[/bold green]", f"Duration: {format_seconds(live_sec)}")
    elif pid is not None:
        table.add_row("Active Session", "[bold green]✓ Starting[/bold green]", "Tracking active window")
    else:
        table.add_row("Active Session", "[bold dim]○ Inactive[/bold dim]", "No active session")

    # // 8. Database Records Health
    all_sessions = get_all_sessions()
    total_records = len(all_sessions)
    if total_records > 0:
        table.add_row("Database Sessions", "[bold green]✓ Valid[/bold green]", f"{total_records} recorded sessions")
    else:
        table.add_row("Database Sessions", "[bold dim]○ Empty[/bold dim]", "0 sessions recorded")

    # // 9. Project Attribution Ratio
    total_screen_time = sum(s["duration_seconds"] for s in all_sessions)
    attr_screen_time = sum(s["duration_seconds"] for s in all_sessions if s.get("project_context") and s["project_context"] != "Unattributed")
    if total_screen_time > 0:
        attr_ratio = (attr_screen_time / total_screen_time * 100)
        table.add_row("Project Attribution", "[bold green]✓ Tracked[/bold green]", f"{attr_ratio:.0f}% attributed ({format_seconds(attr_screen_time)})")
    else:
        table.add_row("Project Attribution", "[bold dim]— Untracked[/bold dim]", "No session data")

    # // 10. Git CLI Check
    git_bin = shutil.which("git")
    if git_bin:
        table.add_row("Git Integration", "[bold green]✓ Available[/bold green]", f"Path: {git_bin}")
    else:
        table.add_row("Git Integration", "[bold yellow]! Not Found[/bold yellow]", "Git CLI missing from PATH")

    # // 11. Log File Status
    if os.path.exists(LOG_FILE):
        size_kb = os.path.getsize(LOG_FILE) / 1024.0
        table.add_row("Daemon Log", "[bold green]✓ Logged[/bold green]", f"{size_kb:.1f} KB ({LOG_FILE})")
    else:
        table.add_row("Daemon Log", "[bold dim]○ Empty[/bold dim]", "Log file not created yet")

    console.print(table)
    console.print("\n[bold green]All core subsystems verified.[/bold green]\n")
