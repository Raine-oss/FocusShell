# // Imports
import os
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

# // Native X11 Idle Detector
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

# // Native Wayland / Sway / Hyprland Idle Fallback
def get_idle_seconds_wayland() -> Optional[float]:
    try:
        out = subprocess.check_output(["swayidle", "-w", "timeout", "1", "true"], stderr=subprocess.DEVNULL)
        return 0.0
    except Exception:
        return None

# // Unified Idle Checker
def get_idle_seconds() -> float:
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
