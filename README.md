# GM-AI-Hub Desktop

> Local-first AI document system for Korean public officers
> 대한민국 공무원을 위한 로컬 AI 공문서 시스템 — 설치형 Windows 데스크톱 앱 (v3.4.0)

All AI processing runs on **your local PC**. No documents or voice data leave the building.
모든 AI 처리는 **로컬 PC**에서 수행됩니다. 문서·음성 데이터가 외부 서버로 전송되지 않습니다.

[![License: GM-Social v1.0](https://img.shields.io/badge/License-GM--Social%20v1.0-blue)](LICENSE)

---

## Features / 주요 기능

| Feature | Description |
|---|---|
| Official Document Drafting (기안문) | AI-generated body text, regulation validation, HWPX export |
| Meeting Minutes (회의록) | Audio recording/upload → STT → AI summary → HWPX |
| AI Chat (AI 채팅) | Streaming conversation, thinking mode, web URL auto-summary |
| Complaint Response (민원 답변) | Complaint type classification → draft response |
| Document Search (문서 검색) | Keyword + vector hybrid search |
| Regulation Search (법령 검색) | Full-text search over national and local regulations (FTS5) |
| PII Management (PII 관리) | Automatic personal info detection and masking |
| Document Diff (문서 비교) | Visual comparison of two documents |
| File Manager (파일 관리) | Workspace file browser |
| Settings (설정) | Department/officer info, Ollama URL, model management |

---

## Tech Stack / 기술 스택

```
Frontend   React 18 + Vite  (SPA, localhost:8080)
Backend    FastAPI + uvicorn (Python 3.11+)
AI Engine  Ollama (local LLM, default port 11434)
STT        faster-whisper medium (local CPU, optional)
DB         SQLite + aiosqlite (WAL mode, FTS5)
Bundle     PyInstaller → Inno Setup 6
```

---

## Quick Start / 빠른 시작

### Prerequisites / 요구사항

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com/download) installed and running

### Development / 개발 환경

```bash
# 1. Install dependencies / 의존성 설치
pip install -e ".[dev]"
npm install --prefix frontend

# 2. Download recommended AI models / AI 모델 다운로드 (first run)
ollama pull qwen3:14b
ollama pull nomic-embed-text

# 3. Start dev servers / 개발 서버 실행
python -m backend.main          # Backend (port 8080)
npm run dev --prefix frontend   # Frontend (port 5173)
```

> In development, access via port 5173. After build, the backend serves `frontend/dist` as static files.
> 개발 시에는 포트 5173, 빌드 후에는 백엔드가 `frontend/dist`를 정적 파일로 서빙합니다.

---

## Build (Windows Installer) / 빌드

```bash
python build/build.py
```

Steps:
1. **Frontend build** — `npm run build`
2. **Tests** — `pytest`
3. **PyInstaller** — creates `dist/GM-AI-Hub/`
4. **Inno Setup** — creates `installer/Output/GM-AI-Hub-Setup-x.x.x.exe`

---

## Project Structure / 프로젝트 구조

```
gm-ai-hub-app/
├── backend/
│   ├── api/           # FastAPI routers
│   ├── ai/            # LLM client, DSPy pipelines, model registry
│   ├── db/
│   │   ├── database.py        # SQLite init (WAL mode)
│   │   └── migrations/        # SQL migrations (001~006)
│   ├── models/        # Pydantic request/response models
│   ├── services/      # hwpx, stt, pii, regulation search services
│   └── main.py        # uvicorn entry point
├── launcher/
│   └── tray.py        # System tray launcher (pystray)
├── frontend/
│   └── src/
│       ├── pages/     # React page components
│       ├── components/# Shared components
│       ├── hooks/     # Custom hooks
│       ├── styles/    # CSS
│       └── utils/     # API helpers
├── build/
│   ├── build.py       # Master build script
│   └── gm-ai-hub.spec # PyInstaller spec
├── installer/
│   └── gm-ai-hub.iss  # Inno Setup script
├── data/
│   └── regulations/   # Regulation PDFs and extracted text
├── scripts/           # Utility scripts
└── tests/             # pytest tests
```

---

## Environment Variables / 환경 변수

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen3:14b` | Default LLM model |
| `WORKING_DIR` | `%USERPROFILE%\Documents\GM-AI-Hub` | Document storage |
| `GM_ENV` | `govpc` | Environment profile (govpc/laptop/desktop) |

---

## Contributing / 기여하기

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
기여 가이드라인은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

---

## License / 라이선스

**[GM-Social License v1.0](LICENSE)**

This project is free to use, modify, and distribute. The one unique condition:
if you deploy it, take a moment to discover Gwangmyeong (광명) and share your
gratitude with the world. See [GRATITUDE.md](GRATITUDE.md).

본 프로젝트는 자유롭게 사용, 수정, 배포할 수 있습니다. 단 하나의 특별한 조건:
배포 시 잠시 시간을 내어 광명(光明)을 발견하고 세상에 감사를 나눠주세요.
[GRATITUDE.md](GRATITUDE.md)를 참조하세요.

---

## Origin / 탄생 이야기

This software was built by a citizen of **Gwangmyeong (광명시), Gyeonggi-do (경기도)**,
Republic of Korea — as a volunteer project, with generative AI as a co-creation tool.
No government funded this. No institution commissioned it. Just a neighbor who wanted
to help public officers work better.

이 소프트웨어는 대한민국 **경기도 광명시**의 한 시민이 자발적으로, 생성형 AI를
공동 창작 도구로 활용하여 만들었습니다. 정부의 지원도, 기관의 의뢰도 없었습니다.
공무원들이 더 잘 일할 수 있도록 돕고 싶었던 이웃의 프로젝트입니다.

*"Share freely. Give credit. Discover Gwangmyeong (광명)."*
*"자유롭게 나누고, 출처를 밝히고, 광명을 발견하세요."*
