# // Imports
from typing import Dict

# // Display Names Mapping
# // Display Names Mapping
APP_NAME_MAP: Dict[str, str] = {
    # // Linux & Generic Editors
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
    
    # // Windows Specific Executables & Consoles
    "windowsterminal.exe": "Windows Terminal",
    "windowsterminal": "Windows Terminal",
    "powershell.exe": "PowerShell",
    "powershell": "PowerShell",
    "pwsh.exe": "PowerShell",
    "pwsh": "PowerShell",
    "cmd.exe": "Command Prompt",
    "cmd": "Command Prompt",
    "explorer.exe": "Windows Explorer",
    "explorer": "Windows Explorer",
    "devenv.exe": "Visual Studio",
    "devenv": "Visual Studio",
    "idea64.exe": "IntelliJ IDEA",
    "idea64": "IntelliJ IDEA",
    "idea.exe": "IntelliJ IDEA",
    "idea": "IntelliJ IDEA",
    "pycharm64.exe": "PyCharm",
    "pycharm64": "PyCharm",
    "pycharm.exe": "PyCharm",
    "pycharm": "PyCharm",
    "clion64.exe": "CLion",
    "clion64": "CLion",
    "clion.exe": "CLion",
    "clion": "CLion",
    "webstorm64.exe": "WebStorm",
    "webstorm64": "WebStorm",
    "webstorm.exe": "WebStorm",
    "webstorm": "WebStorm",
    "code.exe": "VS Code",
    "chrome.exe": "Google Chrome",
    "brave.exe": "Brave",
    "firefox.exe": "Firefox",
    "msedge.exe": "Microsoft Edge",
    "msedge": "Microsoft Edge",
    "notepad.exe": "Notepad",
    "notepad": "Notepad",
    
    # // macOS Specific Apps & Terminals
    "iterm2": "iTerm2",
    "iterm": "iTerm2",
    "terminal": "Terminal",
    "safari": "Safari",
    "finder": "Finder",
    "xcode": "Xcode",
    "activity monitor": "Activity Monitor",
    
    # // Browsers
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
    
    # // IDEs & Text Editors
    "code": "VS Code",
    "vscode": "VS Code",
    "vscodium": "VSCodium",
    "cursor": "Cursor",
    "antigravity ide": "Antigravity",
    "antigravity": "Antigravity",
    "sublime_text": "Sublime Text",
    "sublime": "Sublime Text",
    
    # // Communication & Productivity
    "discord": "Discord",
    "telegram-desktop": "Telegram",
    "telegramdesktop": "Telegram",
    "telegram": "Telegram",
    "slack": "Slack",
    "whatsapp": "WhatsApp",
    "signal": "Signal",
    "thunderbird": "Thunderbird",
    
    # // Media & Entertainment
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
    
    for ext in (".exe", ".app", ".bin", ".x86_64", ".amd64", ".elf"):
        if lowered.endswith(ext):
            lowered = lowered[:-len(ext)]
            cleaned = cleaned[:-len(ext)]
            break
            
    if lowered in APP_NAME_MAP:
        return APP_NAME_MAP[lowered]
        
    for key, display in APP_NAME_MAP.items():
        if key in lowered:
            return display
            
    # // Fallback Cleanup
    parts = cleaned.replace("_", " ").replace("-", " ").replace(".", " ").split()
    if parts:
        res = " ".join([p.capitalize() for p in parts])
        if res.startswith("Gnome "):
            res = "GNOME " + res[6:]
        return res
    return cleaned
