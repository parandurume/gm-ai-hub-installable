# GM-AI-Hub Desktop App — Walkthrough

## Overview

GM-AI-Hub Desktop is an installable Windows application for Korean government officers.
It provides AI-powered document creation, meeting summaries, complaint drafting, and more —
all running locally with Ollama (no cloud dependency).

This project was forked from the original developer-focused GM-AI-Hub (`gm-pub-officer-mcp`)
and restructured for end-user distribution.

---

## Project Structure

```
gm-ai-hub-app/
├── backend/                    # FastAPI server (Python 3.13)
│   ├── paths.py                # Path resolution (frozen vs dev mode)
│   ├── main.py                 # App entry point + SPA serving
│   ├── config.py               # Pydantic Settings (.env based)
│   ├── api/                    # API endpoints
│   │   ├── router.py           # Route registration
│   │   ├── health.py           # /api/health
│   │   ├── setup_wizard.py     # /api/setup/* (first-run wizard)
│   │   ├── draft.py             # Document creation
│   │   ├── chat.py             # AI chat (WebSocket)
│   │   └── ...                 # 12 more routers
│   ├── db/
│   │   ├── database.py         # SQLite + aiosqlite
│   │   └── migrations/         # SQL migration files (001-003)
│   ├── services/
│   │   ├── hwpx_service.py     # HWPX (Korean word processor) ZIP generation
│   │   ├── md_to_owpml.py      # Markdown to OWPML XML converter
│   │   └── ...
│   ├── ai/                     # DSPy pipelines + optimization
│   └── models/                 # Pydantic data models
│
├── frontend/                   # React + Vite SPA
│   ├── src/
│   │   ├── App.jsx             # Routes + SetupGuard (first-run redirect)
│   │   ├── pages/
│   │   │   ├── SetupWizard.jsx # 5-step onboarding wizard
│   │   │   ├── Dashboard.jsx
│   │   │   ├── DraftPage.jsx   # Document creation
│   │   │   ├── ChatPage.jsx    # AI chat with streaming
│   │   │   └── ...             # 8 more pages
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Topbar.jsx
│   │   │   └── ...
│   │   ├── styles/             # CSS design system
│   │   └── utils/api.js        # API endpoint constants + fetch helpers
│   └── dist/                   # Build output (gitignored)
│
├── launcher/                   # System tray (pystray)
│   ├── tray.py                 # TrayApp: manages server subprocess + browser
│   ├── icon.ico                # Windows tray icon
│   └── icon.png
│
├── data/                       # Bundled read-only data
│   ├── examples/               # DSPy training examples (JSON)
│   └── templates/
│
├── build/                      # Build pipeline
│   ├── build.py                # Master build script
│   ├── gm-ai-hub.spec          # PyInstaller spec (two executables)
│   └── hooks/                  # PyInstaller hooks (uvicorn, backend)
│
├── installer/                  # Inno Setup
│   ├── gm-ai-hub.iss           # Installer script (Korean)
│   └── license_ko.txt
│
├── tests/                      # 93 tests
│   ├── test_hwpx.py            # HWPX creation/read/edit/validate
│   ├── test_md_to_owpml.py     # Markdown to OWPML conversion
│   ├── test_md_to_owpml_fixes.py  # Bug fix regression tests
│   ├── test_paths.py           # Path resolution tests
│   └── ...
│
├── pyproject.toml              # Dependencies + entry points
├── .env.example                # Config template
└── WALKTHROUGH.md              # This file
```

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Fork strategy | Full copy | 13 files needed modification; shared-import would be fragile |
| Path resolution | `backend/paths.py` | Single module handles frozen (PyInstaller) vs dev mode |
| User data location | `%LOCALAPPDATA%\GM-AI-Hub\` | Windows standard, survives app updates |
| Tray launcher | pystray (Python) | Same ecosystem, PyInstaller bundles seamlessly |
| PyInstaller mode | One-folder | One-file has 5-15s startup delay; one-folder starts instantly |
| Installer | Inno Setup | Best Windows UX, Korean language, `.iss` is maintainable |
| Ollama | Check only, don't bundle | 300+MB, updates frequently; setup wizard guides installation |

---

## Path Architecture (`backend/paths.py`)

All file paths flow through `paths.py`, which distinguishes two modes:

**Development mode** (`python -m backend.main`):
- Bundle paths = project root (where `pyproject.toml` lives)
- User data paths = `%LOCALAPPDATA%\GM-AI-Hub\`

**Frozen mode** (PyInstaller `.exe`):
- Bundle paths = `sys._MEIPASS` (temporary extraction directory)
- User data paths = `%LOCALAPPDATA%\GM-AI-Hub\` (same)

Key functions:
```python
paths.is_frozen()           # True inside PyInstaller bundle
paths.bundle_dir()          # Read-only: migrations, examples, frontend
paths.app_data_dir()        # Read-write: %LOCALAPPDATA%\GM-AI-Hub
paths.migrations_dir()      # SQL files for DB schema
paths.frontend_dist()       # React build output
paths.db_path()             # SQLite database file
paths.workspace_dir()       # User's working documents
paths.exports_dir()         # Exported HWPX files
```

---

## HWPX Bug Fixes (from original)

Three bugs were fixed in `md_to_owpml.py`:

1. **`<br>` in table cells** — `_make_table()` was constructing `<hp:run>` directly
   with raw cell text, bypassing `_clean_inline()`. Result: `&lt;br&gt;` appeared
   as literal text in HWP.

2. **`**bold**` in table cells** — Same root cause. `_make_runs()` was not called
   for table cell content, so `**text**` appeared with literal asterisks.

3. **Triple-backtick code fences** — `parse_md_blocks()` had no code fence detection.
   Lines like `` ```python `` passed through as regular paragraphs.

**Fix:** Table cells now route through `_make_runs(_clean_inline(val), char_id)`.
Code fences are detected with `_CODE_FENCE_RE` and emitted as literal text blocks.
10 regression tests in `test_md_to_owpml_fixes.py`.

---

## Setup Wizard

On first launch, the app redirects to `/setup` (a 5-step wizard):

1. **Welcome** — App description and feature list
2. **Ollama Check** — Probes `http://127.0.0.1:11434`, shows download link if missing
3. **Model Check** — Lists installed models, shows `ollama pull` commands for missing ones
4. **Department Info** — Department name, officer name (auto-fills documents)
5. **Ready** — Summary and "Start" button

The `SetupGuard` component in `App.jsx` checks `/api/setup/status` on mount.
If `setup_completed` is `false` in the database, it redirects to `/setup`.

---

## System Tray Launcher (`launcher/tray.py`)

The tray app:
1. Starts the FastAPI server as a subprocess (hidden console)
2. Polls `/api/health` until the server responds (up to 30 seconds)
3. Opens the default browser to `http://localhost:8080`
4. Shows a tray icon with menu: Open, Restart, Stop, Quit

In frozen mode, it looks for `gm-hub-server.exe` in the same directory.
In dev mode, it runs `python -m backend.main`.

---

## Development Setup

```bash
# Clone and enter the project
cd /path/to/gm-ai-hub-app

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests (93 tests)
pytest tests/ -v

# Start the backend server (dev mode)
python -m backend.main

# Build the frontend (separate terminal)
cd frontend
npm install
npx vite build
```

---

## Building the Installer

### Prerequisites
- Python 3.11+ with PyInstaller (`pip install pyinstaller`)
- Node.js 18+ with npm
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (optional, for `.exe` installer)

### Clean Build Environment (Recommended)

Always build from a dedicated virtual environment to avoid bundling unrelated packages
(torch, tensorflow, scipy, etc.) that slow down PyInstaller and bloat the installer.

```bash
# Create clean build venv (one-time)
python -m venv .buildenv
.buildenv\Scripts\activate
pip install -e ".[stt,dev]"
```

### Full Build
```bash
# Activate build venv first
.buildenv\Scripts\activate
python build/build.py
```

This runs four steps:
1. `npm install` + `npx vite build` (frontend)
2. `pytest tests/ -v` (all 93 tests)
3. `pyinstaller build/gm-ai-hub.spec` (creates `dist/GM-AI-Hub/`)
4. `ISCC installer/gm-ai-hub.iss` (creates `installer/Output/GM-AI-Hub-Setup-2.0.0.exe`)

### Build Options
```bash
python build/build.py --skip-tests      # Skip pytest
python build/build.py --skip-installer   # Skip Inno Setup
python build/build.py --frontend-only    # Only build React
```

### Build Output
```
dist/GM-AI-Hub/
├── GM-AI-Hub.exe          # Tray launcher (windowed, no console)
├── gm-hub-server.exe      # FastAPI server (console, hidden by launcher)
├── frontend/dist/          # Bundled React app
├── backend/db/migrations/  # SQL migration files
├── data/                   # Examples and templates
└── (Python runtime + dependencies)
```

---

## Commit History

| Commit | Description |
|--------|-------------|
| `5f1d641` | Fork from original project (72 tests, MCP excluded) |
| `e13fc11` | Path abstraction: `paths.py` + 7 modified files + 11 tests |
| `11a9367` | HWPX bug fixes: table `<br>`, `**bold**`, code fences + 10 tests |
| `cd2bf94` | Setup wizard: backend API + frontend 5-step wizard |
| `c4876c9` | System tray launcher: pystray with auto-generated icons |
| `a8fe132` | PyInstaller spec: two-exe one-folder bundle |
| `b936274` | Inno Setup installer: Korean, Ollama check |
| `0d6b881` | Build script: `build/build.py` |

---

## End-User Flow

1. Run `GM-AI-Hub-Setup-2.0.0.exe`
2. Install to Program Files (Ollama download prompted if missing)
3. Launch from Start Menu or Desktop shortcut
4. Tray icon appears; browser opens to `http://localhost:8080`
5. First run: setup wizard guides Ollama, model, and department config
6. Dashboard shows system status; sidebar navigates to all features
7. Create documents, chat with AI, search — all data stays local
