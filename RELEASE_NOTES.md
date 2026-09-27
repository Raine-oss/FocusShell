# Release Notes

All notable changes to the FocusShell project are documented in this file.

---

## [v0.1.1] - 2026-09-27

### Added
- **Structured Daily Review (`focusshell review`)**: Factual, non-judgmental daily reflection answering what occurred during the day without gamified productivity scores.
- **Compact & JSON Review Modes**: Added `focusshell review --compact` for fast terminal checks and `focusshell review --json` for automation and external dashboard integration.
- **Interactive Focus Mode (`focusshell focus <duration> [project]`)**: Live terminal focus tracking session with real-time focus percentage, interruption tracking, and end-of-session summary card.
- **Behavioral Insights Engine (`focusshell insights`)**: Identifies peak activity windows, longest uninterrupted working sessions, context transitions, and distraction breakdowns.
- **Project Context Memory (`focusshell project <name>`)**: Detailed per-project analytics displaying total time, tracked session records, files worked on, and recent activity logs.
- **Timeline Transition Analysis (`focusshell timeline`)**: Complete chronological log detailing transition causes (`App switch`, `Project switch`, `Context switch`, `Idle / Break`) and activity flow sequences.
- **Daily Goals & Progress Tracking (`focusshell goal` & `focusshell progress`)**: Non-gamified target tracking with visual progress bars and remaining time metrics.
- **Comprehensive Diagnostic Doctor (`focusshell doctor`)**: 11-point subsystem verification covering display server, window capture, idle detector, database integrity, process locking, and Git integration.
- **Structured JSON & CSV Exporters (`focusshell export`)**: Direct export to `.json` or `.csv` files.

### Changed
- **Git Root Project Attribution**: Project identity is resolved strictly via Git repository root discovery across workspace trees, completely eliminating window title fragment leaks into project names.
- **Application Opens De-duplication**: Fixed application switches counter to track true application entries without inflating on intra-app file switches.
- **Single Snapshot Aggregation**: Ensured all sections of `focusshell review` use an immutable single-pass database snapshot, guaranteeing 100% calculation consistency across metrics.
- **Display Name Normalization**: Normalized system tools (e.g. `GNOME Terminal`, `GNOME System Monitor`).

### Fixed
- Fixed live active session duration reporting in `focusshell status` and `doctor`.
- Fixed Zed and JetBrains window context extraction edge cases.
- Fixed stale session sealing and crash recovery on unexpected shutdown.

---

## [v0.1.0] - 2026-09-27

### Initial Release
- Core tracking loop with X11 `_NET_ACTIVE_WINDOW` capture and `XScreenSaver` idle detection.
- SQLite WAL storage engine with transactional integrity.
- Background daemon lifecycle management with PID file locking and signal handling.
- Basic terminal analytics (`today`, `report`, `week`, `trends`, `apps`, `top`, `categorize`, `config`).
