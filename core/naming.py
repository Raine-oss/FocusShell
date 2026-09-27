# // Imports
from typing import Dict

# // Display Names Mapping
APP_NAME_MAP: Dict[str, str] = {
    "dev.zed.zed": "Zed",
    "zed": "Zed",
    "gnome-terminal": "GNOME Terminal",
    "gnome-terminal-server": "GNOME Terminal",
    "gnome terminal": "GNOME Terminal",
    "gnome-system-monitor": "GNOME System Monitor",
    "gnome system monitor": "GNOME System Monitor",
    "alacritty": "Alacritty",
    "kitty": "Kitty",
    "wezterm": "WezTerm",
    "ghostty": "Ghostty",
    "konsole": "Konsole",
    "xterm": "XTerm",
    
    "brave-browser": "Brave",
    "brave": "Brave",
    "google-chrome": "Google Chrome",
    "chrome": "Google Chrome",
    "chromium": "Chromium",
    "firefox": "Firefox",
    "zen": "Zen Browser",
    "librewolf": "LibreWolf",
    "opera": "Opera",
    "vivaldi": "Vivaldi",
    "microsoft-edge": "Microsoft Edge",
    
    "code": "VS Code",
    "vscode": "VS Code",
    "vscodium": "VSCodium",
    "cursor": "Cursor",
    "antigravity ide": "Antigravity",
    "antigravity": "Antigravity",
    "sublime_text": "Sublime Text",
    "sublime": "Sublime Text",
    
    "discord": "Discord",
    "telegram-desktop": "Telegram",
    "telegramdesktop": "Telegram",
    "telegram": "Telegram",
    "slack": "Slack",
    "whatsapp": "WhatsApp",
    "signal": "Signal",
    "thunderbird": "Thunderbird",
    
    "spotify": "Spotify",
    "vlc": "VLC",
    "mpv": "MPV",
    "obs": "OBS Studio",
    "obsidian": "Obsidian",
    "notion": "Notion",
    "steam": "Steam",
    "minecraft": "Minecraft"
}

# // Application Normalizer
def normalize_app_name(raw_name: str) -> str:
    if not raw_name or not raw_name.strip():
        return "Unknown"
        
    cleaned = raw_name.strip()
    lowered = cleaned.lower()
    
    if lowered in APP_NAME_MAP:
        return APP_NAME_MAP[lowered]
        
    for key, display in APP_NAME_MAP.items():
        if key in lowered:
            return display
            
    # // Fallback Cleanup
    parts = cleaned.replace("_", " ").replace("-", " ").split()
    if parts:
        res = " ".join([p.capitalize() for p in parts])
        if res.startswith("Gnome "):
            res = "GNOME " + res[6:]
        return res
    return cleaned
