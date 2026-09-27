# // Imports
import os
import sys
import re
import ctypes
import ctypes.util
import subprocess
from typing import Optional

# // Structure Definitions
class XScreenSaverInfo(ctypes.Structure):
    _fields_ = [
        ("window", ctypes.c_ulong),
        ("state", ctypes.c_int),
        ("kind", ctypes.c_int),
        ("til_or_since", ctypes.c_ulong),
        ("idle", ctypes.c_ulong),
        ("eventMask", ctypes.c_ulong)
    ]

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint)
    ]

# // Native Windows Idle Detector
def get_idle_seconds_windows() -> Optional[float]:
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return None

# // Native macOS Idle Detector
def get_idle_seconds_macos() -> Optional[float]:
    try:
        cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cg.CGEventSourceSecondsSinceLastEventType.restype = ctypes.c_double
        cg.CGEventSourceSecondsSinceLastEventType.argtypes = [ctypes.c_int, ctypes.c_uint32]
        idle = cg.CGEventSourceSecondsSinceLastEventType(0, 0xFFFFFFFF)
        if idle >= 0:
            return float(idle)
    except Exception:
        pass
    try:
        out = subprocess.check_output(["ioreg", "-c", "IOHIDSystem"], stderr=subprocess.DEVNULL).decode("utf-8")
        for line in out.splitlines():
            if "HIDIdleTime" in line and "=" in line:
                nanos = int(line.split("=")[-1].strip())
                return nanos / 1_000_000_000.0
    except Exception:
        pass
    return None

# // Native Linux X11 Idle Detector
def get_idle_seconds_x11() -> Optional[float]:
    try:
        x11_path = ctypes.util.find_library("X11") or "libX11.so.6"
        xss_path = ctypes.util.find_library("Xss") or "libXss.so.1"
        
        x11 = ctypes.cdll.LoadLibrary(x11_path)
        xss = ctypes.cdll.LoadLibrary(xss_path)
        
        display = x11.XOpenDisplay(None)
        if not display:
            return None
            
        xss_info = xss.XScreenSaverAllocInfo()
        root = x11.XDefaultRootWindow(display)
        xss.XScreenSaverQueryInfo(display, root, xss_info)
        info = XScreenSaverInfo.from_address(xss_info)
        idle_ms = info.idle
        
        x11.XFree(xss_info)
        x11.XCloseDisplay(display)
        
        return idle_ms / 1000.0
    except Exception:
        return None

# // Native Linux Wayland Idle Detector
def get_idle_seconds_wayland() -> Optional[float]:
    try:
        out = subprocess.check_output([
            "gdbus", "call", "--session",
            "--dest", "org.gnome.Mutter.IdleMonitor",
            "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
            "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime"
        ], stderr=subprocess.DEVNULL).decode("utf-8")
        match = re.search(r"\(uint64\s+(\d+),\)", out) or re.search(r"\((\d+),\)", out)
        if match:
            return int(match.group(1)) / 1000.0
    except Exception:
        pass
    try:
        out = subprocess.check_output([
            "qdbus", "org.freedesktop.ScreenSaver", "/ScreenSaver", "GetSessionIdleTime"
        ], stderr=subprocess.DEVNULL).decode("utf-8")
        return int(out.strip()) / 1000.0
    except Exception:
        pass
    try:
        out = subprocess.check_output(["swayidle", "-w", "timeout", "1", "true"], stderr=subprocess.DEVNULL)
        return 0.0
    except Exception:
        pass
    return None

# // Unified Idle Checker
def get_idle_seconds() -> float:
    if sys.platform.startswith("win"):
        win_idle = get_idle_seconds_windows()
        if win_idle is not None:
            return win_idle
        return 0.0
        
    if sys.platform == "darwin":
        mac_idle = get_idle_seconds_macos()
        if mac_idle is not None:
            return mac_idle
        return 0.0
        
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "x11" or not session_type:
        idle_x11 = get_idle_seconds_x11()
        if idle_x11 is not None:
            return idle_x11
            
    if session_type == "wayland":
        idle_wl = get_idle_seconds_wayland()
        if idle_wl is not None:
            return idle_wl
            
    return 0.0
