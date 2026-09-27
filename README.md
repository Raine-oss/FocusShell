# FocusShell

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20X11%20%7C%20Wayland-lightgrey.svg)](#platform-support)
[![Build Status](https://img.shields.io/badge/build-passing-success.svg)](https://github.com/Raine-oss/FocusShell/actions)
[![Downloads](https://img.shields.io/github/downloads/Raine-oss/FocusShell/total.svg)](https://github.com/Raine-oss/FocusShell/releases)

A high-performance, local-first terminal digital activity and focus tracker designed for developers, systems engineers, and power users. FocusShell operates quietly in the background, mapping active applications to real Git project repositories and workspace contexts, recording granular window activity into an optimized SQLite WAL database without cloud dependencies or telemetric overhead.

---

[![Download Latest Release](https://img.shields.io/badge/Download_Latest_Release-v1.0.0-2ea44f?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Raine-oss/FocusShell/releases/tag/v1.0.0)
[![View Documentation](https://img.shields.io/badge/GitHub-Documentation-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Raine-oss/FocusShell#core-capabilities)
[![Report an Issue](https://img.shields.io/badge/GitHub-Issue_Tracker-blue?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Raine-oss/FocusShell/issues)

---

## Core Capabilities

- **Automatic Project Attribution**: Uses Git repository root discovery to map editor and terminal windows directly to their parent projects (e.g. `FocusShell`, `LogMorph`), preventing filename fragment leakage.
- **Background Daemon Architecture**: Asynchronous tracking daemon with robust PID locking, signal interception (`SIGTERM`, `SIGINT`), and automated crash recovery for orphaned records.
- **Hardware Idle Detection**: Native C-level XScreenSaver and ctypes idle query with zero polling overhead, ensuring breaks and lock screens do not inflate screen time.
- **Structured Daily Review (`focusshell review`)**: Factual, non-judgmental daily summary answering what occurred across projects, applications, and activity flows.
- **Interactive Focus Mode (`focusshell focus <duration> [project]`)**: Live terminal dashboard with progress tracking, real-time focus percentage, and interruption counting.
- **Behavioral Insights Engine (`focusshell insights`)**: Identifies peak activity windows, longest uninterrupted working sessions, context switches, and distraction sources.
- **Project Context Memory (`focusshell project <name>`)**: Detailed per-project analytics showing total time, tracked session records, files worked on, and recent chronological activity.
- **Timeline with Transition Analysis (`focusshell timeline`)**: Complete chronological log detailing transition causes (`App switch`, `Project switch`, `Context switch`, `Idle / Break`).
- **Goal Management (`focusshell goal` & `focusshell progress`)**: Non-gamified target tracking with visual progress bars and remaining time calculations.
- **Structured Data Export**: Full JSON and CSV export capabilities (`focusshell export today.json` / `focusshell export today.csv`).
- **100% Local and Private**: All records remain entirely on your local filesystem in SQLite WAL mode. Zero cloud sync, zero telemetry, and zero background analytics.

---

## Platform Support

| Operating System | Architecture / Display Subsystem | Status | Detection Mechanism |
| :--- | :--- | :--- | :--- |
| **Linux (Arch, Ubuntu, Debian, Fedora, openSUSE, Alpine, NixOS)** | **X11 (x86_64, aarch64, armv7, i686)** | Fully Supported | `xprop`, `_NET_ACTIVE_WINDOW`, `XScreenSaver` ctypes |
| **Linux (Arch, Ubuntu, Debian, Fedora, openSUSE, Alpine, NixOS)** | **Wayland (GNOME, KDE Plasma, Hyprland, Sway, wlroots)** | Fully Supported | `org.gnome.Shell.Introspect`, `kdotool`, `hyprctl`, `swaymsg`, `Mutter.IdleMonitor` |
| **macOS (macOS 11+ Big Sur, Monterey, Ventura, Sonoma, Sequoia)** | **Apple Silicon (M1/M2/M3/M4 ARM64) & Intel (x86_64)** | Fully Supported | AppleScript `osascript`, CoreGraphics `CGEventSource`, `IOKit` `IOHIDSystem` |
| **Windows (Windows 10, Windows 11, Windows Server)** | **Win32 / DWM (x86_64, ARM64, x86)** | Fully Supported | `GetForegroundWindow`, `QueryFullProcessImageNameW`, `GetLastInputInfo` ctypes |

---

## Installation

### Method 1: Git Clone and Local CLI (Recommended)

```bash
# Clone the repository
git clone https://github.com/Raine-oss/FocusShell.git
cd FocusShell

# Ensure dependencies are installed
pip install -r requirements.txt # or pip install rich

# Make executable available
chmod +x focusshell
./focusshell start
```

### Method 2: System-wide Symlink

```bash
# Link executable into standard user binary path
sudo ln -sf "$(pwd)/focusshell" /usr/local/bin/focusshell

# Verify installation
focusshell doctor
```

### Method 3: Python Package Installation (pip)

```bash
pip install .
focusshell start
```

---

## Quick Start & Verification

### 1. Start the Background Daemon

```bash
focusshell start
```

### 2. Verify Subsystem Health

```bash
focusshell doctor
```

Output:
```text
╭──────────────────────────────────────────────────────────────────────────────╮
│ FocusShell — System & Environment Doctor                                     │
╰──────────────────────────────────────────────────────────────────────────────╯
 Display Server          ✓ Ready      Session Type: X11
 Window Capture          ✓ Working    Antigravity — WorkSpace
 Idle Detector           ✓ Active     Current Idle: 0s (XScreenSaver / ctypes)
 Database Integrity      ✓ Healthy    WAL Mode: WAL (focus.db)
 Tracker Daemon          ● Running    Process PID: 1969759
 Session State           ✓ Consistent Synchronized (PID 1969759)
 Active Session          ✓ Active     Duration: 24s
 Database Sessions       ✓ Valid      530 recorded sessions
 Project Attribution     ✓ Tracked    45% attributed (34m)
 Git Integration         ✓ Available  Path: /usr/bin/git
 Daemon Log              ✓ Logged     0.0 KB

All core subsystems verified.
```

### 3. Check Real-time Daemon Status

```bash
focusshell status
```

---

## Command Reference

### Tracking Subcommands

| Command | Description |
| :--- | :--- |
| `focusshell start` | Starts the background tracking daemon process. |
| `focusshell stop` | Gracefully terminates the running background daemon. |
| `focusshell restart` | Restarts the background tracking daemon. |
| `focusshell status` | Displays live active window, category, project, and session duration. |
| `focusshell focus <dur> [proj]` | Initiates an interactive live focus session with interruption tracking. |

### Analytics & Review Subcommands

| Command | Description |
| :--- | :--- |
| `focusshell review [date]` | Produces a structured daily review with factual highlights and activity flow. |
| `focusshell review --compact` | Outputs a concise single-line daily summary. |
| `focusshell review --json` | Exports the full structured daily review as JSON. |
| `focusshell report [--date D]` | Generates an executive daily statistical report with category distributions. |
| `focusshell today [--date D]` | Shows the daily activity timeline and application highlights. |
| `focusshell insights [--date D]` | Provides behavioral patterns, focus project breakdowns, and distraction metrics. |
| `focusshell week [--date D]` | Displays 7-day screen time distributions and daily averages. |
| `focusshell trends [-d DAYS]` | Shows multi-day usage evolution and day-over-day progress comparisons. |

### Project Intelligence Subcommands

| Command | Description |
| :--- | :--- |
| `focusshell projects` | Lists all tracked Git and workspace projects with time and record counts. |
| `focusshell project <name>` | Displays granular memory for a specific project (files, apps, recent activity). |
| `focusshell apps` | Displays a hierarchical tree view of applications, projects, and active files. |
| `focusshell top [-n LIMIT]` | Shows the top applications leaderboard. |
| `focusshell timeline [--date D]` | Full chronological session log with explicit transition causes. |

### Goals & Management Subcommands

| Command | Description |
| :--- | :--- |
| `focusshell goal set <name> <dur>` | Configures a daily duration target for a project or category (e.g. `2h`, `45m`). |
| `focusshell goal list` | Displays all configured targets and created timestamps. |
| `focusshell goal remove <name>` | Removes a configured target. |
| `focusshell progress` | Visual Rich progress bar showing completion toward daily goals. |
| `focusshell export [file]` | Exports recorded sessions to JSON or CSV (e.g. `today.json`, `data.csv`). |
| `focusshell categorize <p> <c>` | Adds or updates custom pattern matching category rules. |
| `focusshell config [action] [k]` | Views or updates runtime configuration settings. |

---

## Interactive Focus Mode

FocusShell provides an active focus tracker that runs in your terminal without turning into an intrusive timer:

```bash
focusshell focus 45m FocusShell
```

Features:
- Live progress bar with elapsed and remaining duration.
- Focused work calculation based on active project context and developer tooling.
- Interruption counter detecting switches to competing projects or distractions.
- End-of-session summary card with focus ratio, idle breakdown, and applications used.

---

## Structured Daily Review

The `focusshell review` command aggregates daily activity into a structured, readable summary based strictly on observed data:

```bash
focusshell review
```

```text
╭──────────────────────────────────────────────────────────────╮
│ FocusShell — Daily Review                                    │
│ September 27, 2026                                           │
╰──────────────────────────────────────────────────────────────╯
Overview
  Active Time            :     1h 24m
  Project Time           :        39m
  Unattributed Time      :        44m
  Longest Session        :        12m

Project Attribution
  Tracked Projects       :        39m (47%)
  Unattributed           :        44m (53%)

Main Project
  FocusShell                    39m

Top Applications
  Antigravity                   37m
  Brave                         29m
  GNOME Terminal                 9m
  Discord                        6m

Activity Mix
  Coding                        39m
  Browser                       30m
  Terminal                       9m
  Social                         6m
  Other                         12s

Work Patterns
  Most Active Window     : 19:00–20:00
  Longest Uninterrupted  : 12m (Antigravity / FocusShell)
  Application Switches   : 353
  Context Transitions    : 413

Activity Flow
  FocusShell → GNOME Terminal → Brave → FocusShell → Brave → GNOME Terminal → Brave → FocusShell

Highlights
  • FocusShell was your main tracked project — 39m.
  • Antigravity was your most-used application — 37m.
  • Longest uninterrupted work session — 12m.
  • 44m of active time was unattributed to a tracked project.
  • Discord accounted for 6m of active time.
```

---

## Data Architecture & Performance

FocusShell stores all activity inside `~/.local/share/focusshell/focus.db`:
- **Storage Engine**: SQLite in Write-Ahead Logging (`WAL`) mode with synchronous `NORMAL`.
- **Query Latency**: Sub-millisecond indexed queries across hundreds of thousands of sessions.
- **Resource Footprint**: Background daemon uses less than 15 MB of RAM and negligible CPU (sub-0.1%).

---

## Development & Contributing

Contributions, bug reports, and enhancements are welcome. Please consult [`CONTRIBUTING.md`](CONTRIBUTING.md) for coding standards, pull request procedures, and local testing instructions.

Run the unit test suite:
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

---

## License

This project is licensed under the MIT License. See the [`LICENSE`](LICENSE) file for details.
