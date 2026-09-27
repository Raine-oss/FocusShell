# // Imports
import os
import re
import glob
import subprocess
from typing import Tuple, Optional

# // Constants & Suffixes
FILE_EXTENSIONS = (
    ".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".c", ".cpp", ".h", 
    ".java", ".html", ".css", ".md", ".json", ".toml", ".yaml", ".yml", ".sh",
    ".txt", ".sql", ".xml", ".ini", ".cfg", ".lock", ".gitignore", ".gitmodules",
    ".dockerignore", ".env", ".vue", ".svelte"
)

APP_SUFFIXES = (
    "visual studio code", "code", "vscodium", "cursor", "antigravity ide",
    "antigravity", "zed", "dev.zed.zed", "sublime text", "pycharm", "intellij",
    "webstorm", "clion", "brave", "firefox", "google chrome", "chromium", "discord"
)

# // Dynamic Workspace Roots
def get_workspace_roots():
    current_repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cwd = os.getcwd()
    candidates = [
        current_repo,
        cwd,
        os.path.abspath(os.path.join(current_repo, "..")),
        os.path.abspath(os.path.join(cwd, "..")),
        os.path.expanduser("~/Desktop/Worker/WorkSpace"),
        os.path.expanduser("~/Desktop/Worker"),
        os.path.expanduser("~/Projects"),
        os.path.expanduser("~/workspace"),
        os.path.expanduser("~/Development")
    ]
    seen = set()
    roots = []
    for c in candidates:
        if c and os.path.isdir(c) and c not in seen:
            seen.add(c)
            roots.append(c)
    return roots

# // Constants & Suffixes
GENERIC_PROJECT_NAMES = {
    "workspace", "projects", "development", "worker", "src", "code",
    "visual studio code", "antigravity", "antigravity ide", "code", "cursor",
    "vscodium", "zed", "dev.zed.zed", "terminal", "unknown", "none", "unattributed"
}

JETBRAINS_BRACKET = re.compile(r"\[(.*?)\]")
TERMINAL_PATH_RE = re.compile(r"(?:~|\/)(?:[^\/]+\/)*([^\/\s:]+)\s*$")
GITHUB_TITLE_RE = re.compile(r"(?:GitHub\s*[-—–]\s*)?(?:[^\/]+\/)?([a-zA-Z0-9_\-\.]+)(?:\:|\s*[-—–]\s*GitHub)", re.IGNORECASE)

# // Project & Git Resolvers
def is_file_name(name: str) -> bool:
    clean = name.strip().lower().rstrip("●*").strip()
    if not clean:
        return False
    if any(clean.endswith(ext) for ext in FILE_EXTENSIONS):
        return True
    if clean.startswith(".") and len(clean) > 1:
        return True
    if clean in ("makefile", "dockerfile", "license", "gemfile", "procfile", "cargo.lock"):
        return True
    return False

def clean_file_title(raw_title: str) -> str:
    clean = re.sub(r"^[●*]\s*", "", raw_title.strip())
    clean = re.sub(r"\s*[●*]$", "", clean)
    return clean.strip()

def find_git_root_name(path_candidate: str) -> str:
    if not path_candidate:
        return ""
    try:
        cur = os.path.abspath(os.path.expanduser(path_candidate))
        if not os.path.exists(cur):
            return ""
        if os.path.isfile(cur):
            cur = os.path.dirname(cur)
        out = subprocess.check_output(
            ["git", "-C", cur, "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        if out:
            git_name = os.path.basename(out)
            if git_name.lower() not in GENERIC_PROJECT_NAMES and not is_file_name(git_name):
                return git_name
    except Exception:
        pass
    return ""

def resolve_project_from_file_search(file_name: str) -> str:
    clean_f = clean_file_title(file_name)
    if not clean_f:
        return ""
        
    target_base = os.path.basename(clean_f)
    roots = get_workspace_roots()
    
    for r in roots:
        git_name = find_git_root_name(r)
        if git_name:
            if os.path.exists(os.path.join(r, clean_f)) or os.path.exists(os.path.join(r, target_base)):
                return git_name
            matches = glob.glob(f"{r}/**/{target_base}", recursive=True)
            if matches:
                return git_name
                
        try:
            for entry in os.listdir(r):
                proj_dir = os.path.join(r, entry)
                if os.path.isdir(proj_dir) and not entry.startswith("."):
                    if os.path.exists(os.path.join(proj_dir, clean_f)) or os.path.exists(os.path.join(proj_dir, target_base)):
                        child_git = find_git_root_name(proj_dir)
                        if child_git:
                            return child_git
                        if entry.lower() not in GENERIC_PROJECT_NAMES and not is_file_name(entry):
                            return entry
                    matches = glob.glob(f"{proj_dir}/**/{target_base}", recursive=True)
                    if matches:
                        child_git = find_git_root_name(proj_dir)
                        if child_git:
                            return child_git
                        if entry.lower() not in GENERIC_PROJECT_NAMES and not is_file_name(entry):
                            return entry
        except Exception:
            pass
            
    return ""

# // Context Extraction Engine
def extract_project_and_context(app_name: str, window_title: str) -> Tuple[str, str]:
    app_lower = app_name.lower().strip()
    title = window_title.strip()
    
    if not title or title == "Unknown":
        return "", "Unknown"
        
    clean_title = clean_file_title(title)
    
    # // JetBrains IDEs
    if any(k in app_lower for k in ("intellij", "pycharm", "webstorm", "clion", "rustrover", "idea")):
        match = JETBRAINS_BRACKET.search(clean_title)
        if match:
            bracket_val = match.group(1).strip()
            git_name = find_git_root_name(bracket_val)
            proj = git_name if git_name else (bracket_val if bracket_val.lower() not in GENERIC_PROJECT_NAMES and not is_file_name(bracket_val) else "")
            parts = [clean_file_title(p) for p in re.split(r"[-—–]", clean_title) if p.strip()]
            file_ctx = clean_title
            for p in parts:
                p_clean = JETBRAINS_BRACKET.sub("", p).strip()
                if is_file_name(p_clean):
                    file_ctx = p_clean
                    break
            if file_ctx == clean_title and parts:
                file_ctx = JETBRAINS_BRACKET.sub("", parts[0]).strip()
            return proj, file_ctx

    # // VS Code / Antigravity / Cursor / VSCodium / Sublime Text
    if any(k in app_lower for k in ("code", "vscode", "vscodium", "cursor", "antigravity", "sublime")):
        parts = [clean_file_title(p) for p in re.split(r"[-—–]", clean_title) if p.strip()]
        filtered = [p for p in parts if p.lower() not in APP_SUFFIXES]
        
        if len(filtered) >= 2:
            part_a = filtered[0]
            part_b = filtered[-1]
            
            if is_file_name(part_b):
                file_candidate = part_b
                proj_candidate = part_a
            elif is_file_name(part_a):
                file_candidate = part_a
                proj_candidate = part_b
            else:
                f_a = resolve_project_from_file_search(part_a)
                f_b = resolve_project_from_file_search(part_b)
                if f_b:
                    file_candidate = part_b
                    proj_candidate = part_a
                elif f_a:
                    file_candidate = part_a
                    proj_candidate = part_b
                else:
                    file_candidate = part_b
                    proj_candidate = part_a
                    
            if proj_candidate and proj_candidate.lower() not in GENERIC_PROJECT_NAMES and not is_file_name(proj_candidate):
                for w_root in get_workspace_roots():
                    cand_path = os.path.join(w_root, proj_candidate)
                    if os.path.exists(cand_path):
                        git_name = find_git_root_name(cand_path)
                        if git_name:
                            return git_name, file_candidate
                        return proj_candidate, file_candidate
                git_name = find_git_root_name(proj_candidate)
                if git_name:
                    return git_name, file_candidate
                return proj_candidate, file_candidate

            resolved_proj = resolve_project_from_file_search(file_candidate)
            if resolved_proj:
                return resolved_proj, file_candidate
                
            return "", file_candidate
            
        elif len(filtered) == 1:
            only_part = filtered[0]
            if only_part.lower() not in GENERIC_PROJECT_NAMES and not is_file_name(only_part):
                for w_root in get_workspace_roots():
                    cand_path = os.path.join(w_root, only_part)
                    if os.path.exists(cand_path):
                        git_name = find_git_root_name(cand_path)
                        if git_name:
                            return git_name, only_part
                git_name = find_git_root_name(only_part)
                if git_name:
                    return git_name, only_part
            resolved_proj = resolve_project_from_file_search(only_part)
            if resolved_proj:
                return resolved_proj, only_part
            if is_file_name(only_part):
                return "", only_part
            return "", only_part
            
    # // Zed Editor
    if "zed" in app_lower:
        parts = [clean_file_title(p) for p in re.split(r"[-—–]", clean_title) if p.strip()]
        filtered = [p for p in parts if p.lower() not in ("zed", "dev.zed.zed")]
        if len(filtered) >= 2:
            proj_cand = filtered[0]
            file_cand = filtered[1]
            if not is_file_name(file_cand) and is_file_name(proj_cand):
                file_cand, proj_cand = proj_cand, file_cand
                
            if proj_cand.lower() not in GENERIC_PROJECT_NAMES and not is_file_name(proj_cand):
                for w_root in get_workspace_roots():
                    cand_path = os.path.join(w_root, proj_cand)
                    if os.path.exists(cand_path):
                        git_name = find_git_root_name(cand_path)
                        if git_name:
                            return git_name, file_cand
                        return proj_cand, file_cand
                git_name = find_git_root_name(proj_cand)
                if git_name:
                    return git_name, file_cand
                return proj_cand, file_cand

            resolved = resolve_project_from_file_search(file_cand)
            if resolved:
                return resolved, file_cand
                
            return "", file_cand
        elif len(filtered) == 1:
            only_part = filtered[0]
            if only_part.lower() not in GENERIC_PROJECT_NAMES and not is_file_name(only_part):
                for w_root in get_workspace_roots():
                    cand_path = os.path.join(w_root, only_part)
                    if os.path.exists(cand_path):
                        git_name = find_git_root_name(cand_path)
                        if git_name:
                            return git_name, only_part
                git_name = find_git_root_name(only_part)
                if git_name:
                    return git_name, only_part
            resolved = resolve_project_from_file_search(only_part)
            if resolved:
                return resolved, only_part
            if is_file_name(only_part):
                return "", only_part
            return "", only_part

    # // Terminal Emulators
    if any(k in app_lower for k in ("terminal", "alacritty", "kitty", "wezterm", "ghostty", "konsole")):
        match = TERMINAL_PATH_RE.search(clean_title)
        if match:
            path_or_folder = match.group(0).strip()
            full_path = os.path.expanduser(path_or_folder)
            git_name = find_git_root_name(full_path)
            if git_name:
                return git_name, clean_title
            folder = match.group(1).strip()
            if folder.lower() not in GENERIC_PROJECT_NAMES and not is_file_name(folder):
                return folder, clean_title
        return "", clean_title

    # // Browsers
    if any(k in app_lower for k in ("brave", "firefox", "chrome", "chromium", "opera", "edge")):
        gh_match = GITHUB_TITLE_RE.search(clean_title)
        if gh_match:
            repo = gh_match.group(1).strip()
            if repo.lower() not in GENERIC_PROJECT_NAMES and not is_file_name(repo):
                for w_root in get_workspace_roots():
                    cand_path = os.path.join(w_root, repo)
                    if os.path.exists(cand_path):
                        git_name = find_git_root_name(cand_path)
                        if git_name:
                            return git_name, f"GitHub: {repo}"
                return repo, f"GitHub: {repo}"
        parts = [clean_file_title(p) for p in re.split(r"[-—–]", clean_title) if p.strip()]
        if parts:
            first = parts[0]
            return "", first
        return "", clean_title

    return "", clean_title

def extract_project_context(app_name: str, window_title: str) -> str:
    proj, _ = extract_project_and_context(app_name, window_title)
    return proj
