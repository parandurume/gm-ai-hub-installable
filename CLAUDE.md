# CLAUDE.md — GM-AI-Hub Desktop

## Project Overview

GM-AI-Hub Desktop is a **local-first AI document system** for Gwangmyeong City Hall (광명시청).
All AI processing runs on the user's local PC via Ollama — no data leaves the machine.

- **Version**: 3.4.0
- **Language**: Korean (한국어) UI and documents
- **License**: Internal use only — 광명시청 정보통신과

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite 5 (SPA, port 5173 dev / 8080 prod) |
| Backend | FastAPI + uvicorn (Python 3.11+) |
| AI Engine | Ollama (local LLM, default port 11434) |
| Default Model | `gpt-oss:20b` (via OpenAI-compatible API) |
| Embedding | `nomic-embed-text` |
| STT | faster-whisper medium (local CPU, optional) |
| Database | SQLite + aiosqlite (WAL mode, FTS5 for regulation search) |
| Desktop | PyInstaller + Inno Setup 6 (Windows installer) |
| System Tray | pystray (launcher/tray.py) |

## Project Structure

```
gm-ai-hub-app/
├── backend/
│   ├── main.py            # FastAPI entry point (uvicorn)
│   ├── config.py           # Pydantic Settings (env-based)
│   ├── paths.py            # Centralized path resolution (frozen/dev)
│   ├── api/
│   │   ├── router.py       # Route registration (try/except pattern)
│   │   ├── health.py, chat.py, draft.py, meeting.py, complaint.py
│   │   ├── regulation.py, search.py, pii.py, diff.py
│   │   ├── settings_api.py, models.py, filesystem.py, samples.py
│   │   └── setup_wizard.py
│   ├── ai/
│   │   ├── client.py        # GptOssClient (Ollama via OpenAI SDK)
│   │   ├── guards.py        # Content safety guards
│   │   ├── pipelines/       # DSPy pipelines (draft, meeting, complaint, docent)
│   │   ├── signatures/      # DSPy signatures
│   │   └── optimization/    # Scheduler, metrics
│   ├── db/
│   │   ├── database.py      # SQLite init, WAL, migrations runner
│   │   └── migrations/      # SQL migration files (001+)
│   ├── models/              # Pydantic request/response models
│   └── services/            # Business logic (hwpx, pii, diff, watcher, index, document)
├── frontend/
│   └── src/
│       ├── App.jsx          # Router with lazy-loaded pages + SetupGuard
│       ├── pages/           # Dashboard, Draft, Meeting, Chat, Complaint, etc.
│       ├── components/      # Sidebar, Topbar, Modal, Toast, etc.
│       ├── hooks/           # Custom hooks (useToast, etc.)
│       ├── styles/          # CSS files
│       └── utils/           # API helpers (fetchJSON, API endpoints)
├── launcher/tray.py         # System tray launcher
├── build/build.py           # Master build script
├── installer/               # Inno Setup script
├── data/regulations/        # Regulation PDFs and extracted text
├── scripts/                 # Utility scripts (build, index, install)
└── tests/                   # pytest tests
```

## Key Architecture Patterns

- **Route registration**: `backend/api/router.py` uses try/except ImportError for each router — allows partial loading
- **AI client**: `backend/ai/client.py` GptOssClient wraps Ollama via OpenAI SDK with `<think>` tag parsing for Qwen3 thinking mode
- **System prompt**: Dynamically injects `date.today().year` — never hardcode years
- **Task reasoning levels**: low/medium/high mapped per task type in `TASK_REASONING` dict
- **Frontend code splitting**: All pages are `React.lazy()` loaded
- **SetupGuard**: First-launch setup wizard redirects until setup is complete
- **DB migrations**: Sequential SQL files in `backend/db/migrations/`, tracked in `_migrations` table
- **Path resolution**: `backend/paths.py` handles both PyInstaller frozen and dev environments
- **Data directory**: `%LOCALAPPDATA%/GM-AI-Hub/` on Windows

## Development

```bash
# Backend (port 8080)
python -m backend.main

# Frontend dev server (port 5173, proxies /api to 8080)
npm run dev --prefix frontend

# Run tests
pytest

# Build installer
python build/build.py
```

## Key Features

| Feature | Route | Page |
|---------|-------|------|
| Dashboard | `/` | Dashboard.jsx |
| Official Document Drafting (기안문) | `/draft` | DraftPage.jsx |
| Meeting Minutes (회의록) | `/meeting` | MeetingPage.jsx |
| AI Chat | `/chat` | ChatPage.jsx |
| Complaint Response (민원 답변) | `/complaint` | ComplaintPage.jsx |
| Regulation Search (법령 검색) | `/regulation` | RegulationPage.jsx |
| Document Search | `/search` | SearchPage.jsx |
| PII Management | `/pii` | PiiPage.jsx |
| Document Diff | `/diff` | DiffPage.jsx |
| File Manager | `/files` | FilesPage.jsx |
| Settings | `/settings` | SettingsPage.jsx |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gpt-oss:20b` | Default LLM model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `APP_HOST` | `127.0.0.1` | Server bind address |
| `APP_PORT` | `8080` | Server port |
| `WORKING_DIR` | `%LOCALAPPDATA%/GM-AI-Hub/workspace` | Document storage |
| `GM_ENV` | auto-detected | Environment profile |

## Conventions

- All backend code is in Korean comments/docstrings
- FastAPI routers use `/api/` prefix
- Frontend uses `fetchJSON()` and `API` object from `utils/api` for all API calls
- Pydantic models in `backend/models/` for request/response schemas
- DSPy pipelines in `backend/ai/pipelines/` for structured AI tasks
