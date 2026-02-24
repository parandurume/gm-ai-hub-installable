# GM-AI-Hub Desktop

> 광명시청 AI 통합 공문서 시스템 — 설치형 Windows 데스크톱 앱

모든 AI 처리는 **로컬 PC**에서 수행됩니다. 문서·음성 데이터가 외부 서버로 전송되지 않습니다.

---

## 주요 기능

| 기능 | 설명 |
|---|---|
| 기안문 작성 | AI 본문 자동 생성, 공문서 규정 검증, HWPX 저장 |
| 회의록 | 음성 녹음 / 파일 업로드 → STT → AI 요약 → HWPX |
| AI 채팅 | 스트리밍 대화, Thinking 모드, 웹 URL 자동 요약 |
| 민원 답변 | 민원 유형 분류 → 답변 초안 생성 |
| 문서 검색 | 키워드·벡터 하이브리드 검색 |
| 법령 검색 | 광명시 규정 전문 검색 |
| PII 관리 | 개인정보 자동 탐지 및 마스킹 |
| 문서 비교 | 두 문서 차이점 시각화 |
| 파일 관리 | 작업 폴더 파일 브라우저 |
| 설정 | 부서·담당자 정보, Ollama URL, 모델 관리 |

---

## 기술 스택

```
Frontend   React 18 + Vite  (SPA, localhost:8080)
Backend    FastAPI + uvicorn (Python 3.11)
AI Engine  Ollama (로컬 LLM, 기본 포트 11434)
STT        faster-whisper medium 모델 (로컬 CPU)
DB         SQLite + aiosqlite (WAL 모드)
Bundle     PyInstaller → Inno Setup 6
```

---

## 개발 환경 구성

### 요구사항

- Python 3.11 이상
- Node.js 20 이상
- [Ollama](https://ollama.com/download) 설치 및 실행

### 빠른 시작

```bash
# 1. 의존성 설치
pip install -e ".[dev]"
npm install --prefix frontend

# 2. 권장 AI 모델 다운로드 (첫 실행 시)
ollama pull qwen3:14b
ollama pull nomic-embed-text

# 3. 개발 서버 실행
python -m backend.main          # 백엔드 (포트 8080)
npm run dev --prefix frontend   # 프론트엔드 (포트 5173)
```

> 개발 시에는 프론트엔드 포트 5173에서 접속하고,
> 빌드 후에는 백엔드가 `frontend/dist`를 정적 파일로 서빙합니다.

---

## 빌드 (Windows 배포용 인스톨러)

```bash
python build/build.py
```

단계:
1. **프론트엔드 빌드** — `npm run build`
2. **테스트** — `pytest`
3. **PyInstaller** — `dist/GM-AI-Hub/` 폴더 생성
4. **Inno Setup** — `installer/Output/GM-AI-Hub-Setup-x.x.x.exe` 생성

> Inno Setup이 없으면 winget으로 자동 설치합니다.

---

## 프로젝트 구조

```
gm-ai-hub-app/
├── backend/
│   ├── api/           # FastAPI 라우터
│   ├── ai/            # LLM 클라이언트, 파이프라인, 모델 레지스트리
│   ├── db/            # SQLite 초기화 및 마이그레이션
│   ├── models/        # Pydantic 요청/응답 모델
│   ├── services/      # hwpx, stt, pii 등 서비스 레이어
│   └── main.py        # uvicorn 진입점
├── launcher/
│   └── tray.py        # 시스템 트레이 런처 (pystray)
├── frontend/
│   └── src/
│       ├── pages/     # React 페이지 컴포넌트
│       ├── components/# 공용 컴포넌트
│       ├── hooks/     # 커스텀 훅
│       ├── styles/    # CSS
│       └── utils/     # API 헬퍼
├── build/
│   ├── build.py       # 마스터 빌드 스크립트
│   └── gm-ai-hub.spec # PyInstaller 스펙
├── installer/
│   └── gm-ai-hub.iss  # Inno Setup 스크립트
├── migrations/        # SQLite 마이그레이션 SQL
└── tests/             # pytest 테스트
```

---

## 환경 변수 (선택)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama 서버 주소 |
| `OLLAMA_MODEL` | `qwen3:14b` | 기본 LLM 모델 |
| `WORKING_DIR` | `%USERPROFILE%\Documents\GM-AI-Hub` | 문서 저장 폴더 |
| `GM_ENV` | `govpc` | 환경 프로필 (govpc/laptop/desktop) |

---

## 라이선스

내부 사용 전용 — 광명시청 정보통신과
