# // Imports
from typing import Dict
from core.database import get_custom_categories

# // Default Categories Mapping
DEFAULT_RULES: Dict[str, str] = {
    "code": "Coding",
    "vscode": "Coding",
    "vscodium": "Coding",
    "cursor": "Coding",
    "neovim": "Coding",
    "nvim": "Coding",
    "vim": "Coding",
    "emacs": "Coding",
    "sublime": "Coding",
    "pycharm": "Coding",
    "intellij": "Coding",
    "webstorm": "Coding",
    "clion": "Coding",
    "rustrover": "Coding",
    "antigravity": "Coding",
    "zed": "Coding",
    "dev.zed.zed": "Coding",
    
    "terminal": "Terminal",
    "alacritty": "Terminal",
    "kitty": "Terminal",
    "wezterm": "Terminal",
    "gnome-terminal": "Terminal",
    "konsole": "Terminal",
    "xterm": "Terminal",
    "tilix": "Terminal",
    "ghostty": "Terminal",
    "foot": "Terminal",

    "firefox": "Browser",
    "chrome": "Browser",
    "chromium": "Browser",
    "brave": "Browser",
    "google-chrome": "Browser",
    "zen": "Browser",
    "librewolf": "Browser",
    "opera": "Browser",
    "vivaldi": "Browser",
    "edge": "Browser",

    "discord": "Social",
    "telegram": "Social",
    "slack": "Social",
    "whatsapp": "Social",
    "signal": "Social",
    "element": "Social",
    "thunderbird": "Social",

    "steam": "Gaming",
    "lutris": "Gaming",
    "heroic": "Gaming",
    "minecraft": "Gaming",
    "prism": "Gaming",
    "retroarch": "Gaming",
    "game": "Gaming",

    "spotify": "Media",
    "vlc": "Media",
    "mpv": "Media",
    "obs": "Media",
    "audacity": "Media",
    "rhythmbox": "Media",

    "obsidian": "Notes",
    "notion": "Notes",
    "logseq": "Notes",
    "libreoffice": "Office",
    "gimp": "Design",
    "inkscape": "Design",
    "figma": "Design",
    "blender": "Design"
}

# // Category Resolver
def categorize_window(app_name: str, window_title: str) -> str:
    app_lower = app_name.lower().strip()
    title_lower = window_title.lower().strip()
    
    try:
        custom_rules = get_custom_categories()
        for pattern, category in custom_rules.items():
            if pattern in app_lower or pattern in title_lower:
                return category
    except Exception:
        pass
        
    for pattern, category in DEFAULT_RULES.items():
        if pattern in app_lower or pattern in title_lower:
            return category
            
    return "Other"
