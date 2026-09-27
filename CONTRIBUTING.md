# Contributing to FocusShell

Thank you for your interest in contributing to FocusShell. We welcome bug reports, feature requests, documentation improvements, and code contributions.

---

## Code of Conduct

Please maintain a constructive, respectful, and professional environment when interacting with other contributors and maintainers.

---

## Development Setup

FocusShell requires Python 3.8+ and standard system libraries (`sqlite3`, `ctypes`, `subprocess`).

### Prerequisites
- Python 3.8 or higher
- `rich>=13.0.0`
- Linux X11 display server or Wayland environment

### Setting Up Local Environment
```bash
# Clone the repository
git clone https://github.com/Raine-oss/FocusShell.git
cd FocusShell

# Create and activate a virtual environment (optional)
python3 -m venv venv
source venv/bin/activate

# Install dependencies in editable mode
pip install -e .
```

### Running the Test Suite
FocusShell includes a comprehensive test suite covering database integrity, daemon lifecycle, crash recovery, project context extraction, daily reviews, and analytical metrics:

```bash
# Run all unit and integration tests
python3 -m unittest discover -s tests -p "test_*.py"
```

### Running Benchmarks
```bash
python3 benches/benchmark_engine.py
```

---

## Code Standards

- **Formatting & Style**: Follow PEP 8 guidelines. Keep functions modular and single-purpose.
- **Section Headers Only**: All code comments must follow the strict section header convention (`# // Header Name`). Do not add inline, explanatory, or educational comments.
- **Error Handling**: Native calls and window capture queries must never crash the background tracking daemon. Wrap system interactions in safe fallbacks.
- **Data Integrity**: Database queries must use parameterized statements to prevent SQL injection and transaction corruption in SQLite WAL mode.

---

## Submitting Pull Requests

1. Fork the repository and create a new feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Make your modifications, adhering to the project's coding standards.
3. Ensure all existing and newly added unit tests pass:
   ```bash
   python3 -m unittest discover -s tests -p "test_*.py"
   ```
4. Commit your changes with descriptive, conventional commit messages (`feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`).
5. Push to your fork and submit a Pull Request against the `main` branch.
