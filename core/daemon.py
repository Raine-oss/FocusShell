# // Imports
import os
import sys
import time
import signal
import subprocess
from typing import Optional, Tuple
from core.config import load_config, DEFAULT_DATA_DIR

# // Paths
PID_FILE = os.path.join(DEFAULT_DATA_DIR, "focusshell.pid")
LOG_FILE = os.path.join(DEFAULT_DATA_DIR, "focusshell.log")

# // Daemon Inspector
def get_daemon_pid() -> Optional[int]:
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
        return None

# // Daemon Controls
def start_daemon(main_script_path: str) -> Tuple[bool, str]:
    existing_pid = get_daemon_pid()
    if existing_pid is not None:
        return False, f"FocusShell daemon is already running (PID: {existing_pid})"
        
    os.makedirs(DEFAULT_DATA_DIR, exist_ok=True)
    
    with open(LOG_FILE, "a") as log_out:
        proc = subprocess.Popen(
            [sys.executable, main_script_path, "daemon-run"],
            stdout=log_out,
            stderr=log_out,
            stdin=subprocess.DEVNULL,
            start_new_session=True
        )
        
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
        
    return True, f"FocusShell daemon started (PID: {proc.pid})"

def stop_daemon() -> Tuple[bool, str]:
    pid = get_daemon_pid()
    if pid is None:
        return False, "FocusShell daemon is not running."
        
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return True, f"FocusShell daemon stopped (PID: {pid})"
    except ProcessLookupError:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return False, "FocusShell daemon was not running (stale PID cleaned)."
    except Exception as e:
        return False, f"Failed to stop daemon: {e}"

def restart_daemon(main_script_path: str) -> Tuple[bool, str]:
    stop_daemon()
    time.sleep(0.5)
    return start_daemon(main_script_path)
