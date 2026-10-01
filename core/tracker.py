# // Imports
import os
import sys
import json
import time
import signal
import shutil
import ctypes
import subprocess
from datetime import datetime
from typing import Tuple, Optional
from core.naming import normalize_app_name
from core.categories import categorize_window
from core.context import extract_project_and_context
from core.config import load_config, DEFAULT_DATA_DIR
from core.idle import get_idle_seconds
from core.database import (
    init_db,
    create_session,
    update_session,
    close_session,
    recover_stale_sessions
)

# // Active State Cache
ACTIVE_STATE_FILE = os.path.join(DEFAULT_DATA_DIR, "active_state.json")

def write_active_state(data: dict) -> None:
    try:
        os.makedirs(DEFAULT_DATA_DIR, exist_ok=True)
        with open(ACTIVE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def clear_active_state() -> None:
    if os.path.exists(ACTIVE_STATE_FILE):
        try:
            os.remove(ACTIVE_STATE_FILE)
        except Exception:
            pass

# // Native Windows Window Fetcher
def get_active_window_windows() -> Tuple[Optional[str], Optional[str]]:
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None, None
            
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or "Unknown"
        
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        app_name = "Unknown"
        h_process = kernel32.OpenProcess(0x1000, False, pid.value)
        if h_process:
            try:
                exe_buf = ctypes.create_unicode_buffer(1024)
                exe_size = ctypes.c_ulong(1024)
                if kernel32.QueryFullProcessImageNameW(h_process, 0, exe_buf, ctypes.byref(exe_size)):
                    app_name = os.path.basename(exe_buf.value)
            finally:
                kernel32.CloseHandle(h_process)
        return app_name, title
    except Exception:
        return None, None

# // Native macOS Window Fetcher
def get_active_window_macos() -> Tuple[Optional[str], Optional[str]]:
    try:
        script = 'tell application "System Events"\n' \
                 '  set frontApp to first application process whose frontmost is true\n' \
                 '  set frontAppName to name of frontApp\n' \
                 '  set frontWindowName to ""\n' \
                 '  try\n' \
                 '    tell frontApp to set frontWindowName to name of first window\n' \
                 '  end try\n' \
                 '  return frontAppName & "\\n" & frontWindowName\n' \
                 'end tell'
        out = subprocess.check_output(["osascript", "-e", script], stderr=subprocess.DEVNULL).decode("utf-8")
        lines = [l.strip() for l in out.splitlines()]
        if lines:
            app_name = lines[0] or "Unknown"
            title = lines[1] if len(lines) > 1 and lines[1] else app_name
            return app_name, title
    except Exception:
        pass
    return None, None

# // Native Linux X11 Window Fetcher
def get_active_window_x11() -> Tuple[Optional[str], Optional[str]]:
    try:
        root_out = subprocess.check_output(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")
        
        parts = root_out.strip().split()
        if not parts:
            return None, None
            
        win_id = parts[-1]
        if win_id in ("0x0", "0", "None"):
            return None, None
        
        prop_out = subprocess.check_output(
            ["xprop", "-id", win_id, "WM_CLASS", "_NET_WM_NAME", "WM_NAME"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")
        
        app_name = "Unknown"
        title = "Unknown"
        
        for line in prop_out.splitlines():
            if "WM_CLASS" in line and "=" in line:
                class_parts = line.split("=", 1)[1].strip().replace('"', '').split(",")
                if class_parts:
                    app_name = class_parts[-1].strip()
            elif ("_NET_WM_NAME" in line or "WM_NAME" in line) and "=" in line:
                if title == "Unknown":
                    raw_title = line.split("=", 1)[1].strip()
                    if raw_title.startswith('"') and raw_title.endswith('"'):
                        raw_title = raw_title[1:-1]
                    title = raw_title
                    
        return app_name, title
    except Exception:
        return None, None

# // Native Linux Wayland Window Fetcher
def get_active_window_wayland() -> Tuple[Optional[str], Optional[str]]:
    try:
        if "HYPRLAND_INSTANCE_SIGNATURE" in os.environ:
            out = subprocess.check_output(["hyprctl", "activewindow", "-j"], stderr=subprocess.DEVNULL).decode("utf-8")
            data = json.loads(out)
            return data.get("class", "Unknown"), data.get("title", "Unknown")
            
        if "SWAYSOCK" in os.environ:
            out = subprocess.check_output(["swaymsg", "-t", "get_tree"], stderr=subprocess.DEVNULL).decode("utf-8")
            def find_focused(node):
                if node.get("focused"):
                    return node.get("app_id") or node.get("window_properties", {}).get("class", "Unknown"), node.get("name", "Unknown")
                for child in node.get("nodes", []) + node.get("floating_nodes", []):
                    res = find_focused(child)
                    if res:
                        return res
                return None
            data = json.loads(out)
            res = find_focused(data)
            if res:
                return res

        if shutil.which("kdotool"):
            win_id = subprocess.check_output(["kdotool", "getactivewindow"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
            if win_id:
                app_name = subprocess.check_output(["kdotool", "getwindowclassname", win_id], stderr=subprocess.DEVNULL).decode("utf-8").strip()
                title = subprocess.check_output(["kdotool", "getwindowname", win_id], stderr=subprocess.DEVNULL).decode("utf-8").strip()
                return app_name or "Unknown", title or "Unknown"
    except Exception:
        pass
    return None, None

# // Unified Active Window Dispatcher
def get_active_window() -> Tuple[Optional[str], Optional[str]]:
    raw_app = None
    title = None
    
    if sys.platform.startswith("win"):
        raw_app, title = get_active_window_windows()
    elif sys.platform == "darwin":
        raw_app, title = get_active_window_macos()
    else:
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if session_type == "wayland":
            raw_app, title = get_active_window_wayland()
            
        if not raw_app:
            raw_app, title = get_active_window_x11()
            
    if raw_app and title:
        norm_app = normalize_app_name(raw_app)
        return norm_app, title
        
    return None, None

# // Tracking State & Signals
_running = True
_active_session_id: Optional[int] = None
_session_start_time: Optional[datetime] = None
_session_active_seconds: int = 0

def _signal_handler(signum, frame):
    global _running
    _running = False

# // Main Tracking Engine
def run_tracking_loop(stop_event=None) -> None:
    global _running, _active_session_id, _session_start_time, _session_active_seconds
    init_db()
    recover_stale_sessions()
    
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _signal_handler)
        
    pid_file = os.path.join(DEFAULT_DATA_DIR, "focusshell.pid")
    try:
        os.makedirs(DEFAULT_DATA_DIR, exist_ok=True)
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    
    cfg = load_config()
    sampling_interval = float(cfg.get("sampling_interval_seconds", 2.0))
    idle_threshold = float(cfg.get("idle_threshold_seconds", 180.0))
    min_session_duration = int(cfg.get("min_session_duration_seconds", 1))
    
    current_app: Optional[str] = None
    current_title: Optional[str] = None
    current_project: str = ""
    is_paused = False
    
    try:
        while _running:
            if stop_event and stop_event():
                break
                
            idle_secs = get_idle_seconds()
            
            # // Idle State Handling
            if idle_secs >= idle_threshold:
                if not is_paused:
                    is_paused = True
                    if _active_session_id is not None and _session_start_time is not None:
                        update_session(_active_session_id, datetime.now(), _session_active_seconds)
                time.sleep(sampling_interval)
                continue
            else:
                if is_paused:
                    is_paused = False
                    
            now = datetime.now()
            app, title = get_active_window()
            
            # // Window Activity Check
            if app and title:
                project_name, file_context = extract_project_and_context(app, title)
                
                if app != current_app or file_context != current_title or project_name != current_project:
                    # // Close Previous Session
                    if _active_session_id is not None and _session_start_time is not None:
                        close_session(
                            session_id=_active_session_id,
                            ended_at=now,
                            duration_seconds=_session_active_seconds,
                            min_duration=min_session_duration
                        )
                    
                    # // Start New Session
                    category = categorize_window(app, file_context)
                    _active_session_id = create_session(
                        app_name=app,
                        window_title=file_context,
                        category=category,
                        project_context=project_name,
                        started_at=now
                    )
                    current_app = app
                    current_title = file_context
                    current_project = project_name
                    _session_start_time = now
                    _session_active_seconds = 1
                else:
                    # // Increment Active Session Duration
                    if _session_start_time is not None:
                        _session_active_seconds = max(1, int((now - _session_start_time).total_seconds()))
                    else:
                        _session_active_seconds += int(sampling_interval)
                        
                    if _active_session_id is not None:
                        update_session(
                            session_id=_active_session_id,
                            ended_at=now,
                            duration_seconds=_session_active_seconds
                        )
                        
                # // Update Live State Cache
                write_active_state({
                    "app_name": current_app,
                    "window_title": current_title,
                    "project_name": current_project,
                    "session_start": _session_start_time.strftime("%Y-%m-%d %H:%M:%S") if _session_start_time else None,
                    "duration_seconds": _session_active_seconds,
                    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                # // No Window Active
                if _active_session_id is not None and _session_start_time is not None:
                    close_session(
                        session_id=_active_session_id,
                        ended_at=now,
                        duration_seconds=_session_active_seconds,
                        min_duration=min_session_duration
                    )
                    _active_session_id = None
                    _session_start_time = None
                    _session_active_seconds = 0
                    current_app = None
                    current_title = None
                    current_project = ""
                    clear_active_state()
                    
            time.sleep(sampling_interval)
    finally:
        # // Termination Flush
        if _active_session_id is not None and _session_start_time is not None:
            close_session(
                session_id=_active_session_id,
                ended_at=datetime.now(),
                duration_seconds=_session_active_seconds,
                min_duration=min_session_duration
            )
        clear_active_state()
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    stored_pid = int(f.read().strip())
                if stored_pid == os.getpid():
                    os.remove(pid_file)
            except Exception:
                pass
