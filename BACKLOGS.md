# GM-AI-Hub 개발 백로그

우선순위: 🔴 High / 🟡 Medium / 🔵 Low
상태: `[ ]` 미착수 / `[~]` 진행 중 / `[x]` 완료

---

## v3.x — 다음 릴리스

### UX 감사 — AI 세션 피드백 및 사용성 개선 (2026-02-27)

> UX 에이전트 전체 감사 결과. 현재 점수 7.0/10 → 목표 8.8/10.
> 핵심 문제: AI 세션 중 진행 상태 피드백 부재 ("화면이 깜깜하다")

#### Sprint 1 — Quick Wins (~2일)

- [x] 🔴 **MeetingPage: AI 생성 중 피드백 없음** — 단계별 Phase labels 추가 (4초 주기 순환, chipIn 애니메이션)
- [x] 🔴 **DraftPage: 첫 토큰 전 빈 화면** — skeleton loader 추가 (`generating && !preview` 분기)
- [x] 🔴 **ChatPage: 경과 시간 표시** — 이미 구현됨 (elapsed timer + 15초 힌트)
- [x] 🟡 **FilesPage: `window.confirm()` → ConfirmModal** — 이미 구현됨
- [x] 🟡 **ChatPage: AI 메시지 복사 버튼** — 이미 구현됨 (handleCopyMessage + checkmark)
- [x] 🟡 **ComplaintPage: 글자 수 카운터** — 이미 구현됨 (MAX_COMPLAINT=3000 + amber/red)
- [x] 🟡 **에러 메시지 개선 (전체)** — `aiErrorMessage()` 헬퍼 추가, DraftPage/MeetingPage/ComplaintPage 적용
- [x] 🟡 **SetupWizard: 레이블 스테퍼 + Ollama 연결 강제** — 번호+이름 스테퍼, 미연결 시 "다음" 비활성화
- [x] 🔵 **SampleManager: `var(--bg2)` → `var(--paper2)`** — 이미 정상 (--bg2 → --paper2 매핑 존재)
- [x] 🔵 **ThinkingPanel: 펼침/접힘 애니메이션** — 이미 구현됨 (0.25s max-height transition)
- [x] 🔵 **Guard chip 등장 애니메이션** — 이미 구현됨 (staggered chipIn scale+fade)

#### Sprint 2 — Core Improvements (~1주)

- [x] 🔴 **Topbar: 글로벌 AI-Busy 표시** — AiBusyContext + useAiBusy 훅, Topbar에 펄스 인디케이터, DraftPage/MeetingPage/ChatPage 연동
- [x] 🔴 **MeetingPage: SSE 스트리밍 전환** — `/api/meeting/stream` SSE 엔드포인트 + 프론트엔드 실시간 스트리밍 (ThinkingPanel 포함)
- [x] 🟡 **Dashboard: 최근 작업 목록** — 최근 문서 8개 표시 (기존 `/api/documents` 활용)
- [x] 🟡 **DiffPage: 줄 번호 + 변경 요약** — 줄 번호 추가, 변경 요약 바 (+추가/-삭제/유사도%), 에러 메시지 개선
- [x] 🟡 **Topbar: Ollama 폴링 주기 단축** — 30초 → 10초

#### Strategic Enhancements (향후)

- [x] 🟡 **법령검색 → AI 채팅 연결** — RegulationPage 미리보기에 "AI에게 물어보기" 버튼 추가, ChatPage `location.state.prefill`로 프롬프트 자동 입력
- [x] 🟡 **DraftPage: 인라인 미리보기 편집** — preview pane에 편집 모드 토글 ("수정"/"완료" 버튼, 완료 시 자동 재검증)
- [x] 🟡 **PII 검사 보고서 내보내기** — HWPX 형식 감사 기록 생성 (`POST /api/pii/export-report`, PiiPage "보고서 내보내기" 버튼)
- [x] 🟡 **SetupWizard: 인앱 모델 다운로드** — step 3에서 EventSource + progress bar로 인앱 모델 다운로드 (SettingsPage 패턴 재사용)

### STT / 회의록

- [ ] 🔴 **STT PyInstaller 패키징** — `faster_whisper`, `ctranslate2` hidden imports를 `build/gm-ai-hub.spec`에 추가하고 `.pyd`/`.dll` 바이너리 포함 확인
- [ ] 🔴 **STT 모델 첫 실행 UX** — 첫 음성 인식 시 모델 다운로드(~1.5 GB)가 시작됨. 설정 페이지에 "STT 모델 다운로드" 버튼 + 진행률 표시 추가
- [ ] 🟡 **실시간 스트리밍 STT** — 녹음 중 WebSocket으로 부분 텍스트를 실시간으로 textarea에 반영 (faster-whisper VAD 기반 청킹)
- [x] 🟡 **STT 모델 설정** — 설정 > 일반 탭에 STT 모델 드롭다운 추가, `meeting.py`에서 DB 설정 읽어 `_get_stt_service()` 캐시 사용
- [ ] 🔵 **회의록 화자 분리** — 발화자별 텍스트 구분 (pyannote.audio + faster-whisper 조합, GPU 필요)

### AI 기능

- [ ] 🔴 **HyperCLOVA X OmniServe 연동** — NAVER Cloud OmniServe API(OpenAI 호환) 옵션 추가. `backend/ai/client.py`에 provider 선택 로직 구현. 인터넷 연결 시 사용 가능한 고성능 한국어 모델.
- [x] 🟡 **기안문 작성에 내 정보 자동 입력** — `draft.py`에 `_load_user_context()` 추가, AI 프롬프트에 부서명·담당자명 자동 주입
- [x] 🟡 **민원 답변에 내 정보 반영** — `complaint.py`에 `_load_user_context()` 추가, AI 프롬프트 + HWPX "담당자" 필드에 자동 삽입
- [x] 🟡 **AI 채팅 히스토리 저장** — SQLite `chat_sessions`+`chat_messages` 테이블, 세션 CRUD API, 프론트엔드 세션 바 자동저장/불러오기
- [ ] 🔵 **RAG 개선** — nomic-embed-text 임베딩 기반 문서 검색을 벡터 DB(ChromaDB)로 전환

### 설정 / UX

- [x] 🟡 **STT 언어 설정** — 설정 > 일반 탭에 STT 언어 드롭다운 추가 (ko/en/ja/zh/auto)
- [x] 🟡 **작업 폴더 선택 다이얼로그** — FolderPicker 컴포넌트로 교체 (설정 > 일반 탭)
- [x] 🔵 **다크 모드** — `[data-theme="dark"]` CSS 변수 오버라이드, `useTheme` 훅 + Topbar 토글 버튼, localStorage 지속
- [ ] 🔵 **앱 자동 업데이트** — 버전 체크 + 새 인스톨러 다운로드 알림

### 빌드 / 배포

- [ ] 🔴 **v3.2.0 재빌드 및 재설치** — 절전 버그 수정 + 환경 감지 수정 + 법령검색 데이터(006) 반영을 위해 `python build/build.py` 실행 후 인스톨러 재배포 필요
- [ ] 🔴 **PyInstaller spec 업데이트** — faster-whisper 추가에 따른 hidden imports:

  ```python
  hiddenimports=['faster_whisper', 'ctranslate2', 'huggingface_hub']
  ```

  ctranslate2 `.dll` 파일을 `binaries` 섹션에 포함해야 할 수 있음
- [x] 🟡 **인스톨러 버전 동기화** — `build.py`에 `_sync_installer_version()` 추가, `step_installer()` 시작 시 pyproject.toml→gm-ai-hub.iss 자동 동기화
- [ ] 🟡 **코드 서명** — Windows Defender 경고 방지를 위한 EV 코드 서명 인증서 적용
- [ ] 🔵 **자동 빌드 CI** — GitHub Actions 또는 로컬 스케줄러로 정기 빌드 자동화

### 보안 / 안정성

- [x] 🟡 **PII 검사 회의록 적용** — `POST /api/pii/scan-text` 엔드포인트 추가, MeetingPage 음성 인식 후 자동 PII 스캔 + 토스트 경고
- [x] 🟡 **API 인증** — `OriginCheckMiddleware`로 POST/PUT/DELETE Origin 헤더 검증, WebSocket origin 체크
- [ ] 🔵 **에러 리포팅** — 오류 발생 시 로컬 로그 파일 자동 수집 + "오류 보고" 버튼

### 역할 관리 (미래 기능)

> 현재는 모든 사용자가 동일한 기능에 접근합니다. 아래 항목은 사용자 수가 증가하거나
> 부서별 배포가 필요해질 때 구현을 검토합니다.
> 페르소나 참고: `USER_STORY.md` — 김민준(주무관), 이수연(팀장), 박정호(정보화 담당)

- [ ] 🔵 **사용자 계정 및 로그인** — 로컬 계정 또는 Active Directory/LDAP 연동
- [ ] 🔵 **역할 기반 접근 제어 (RBAC)** — 일반 사용자 / 검토자 / 관리자 권한 분리. 관리자만 모델 관리·프롬프트 최적화 접근 가능
- [ ] 🔵 **감사 로그 뷰어** — 문서 생성·PII 스캔·설정 변경 이력을 UI에서 확인 (백엔드 로그는 이미 존재)
- [ ] 🔵 **부서별 프로필** — 부서명·담당자 정보를 개인이 아닌 계정에 연결하여 다중 사용자 환경 지원

---

## v2.x — 완료

- [x] 기안문 AI 작성 (기본)
- [x] 회의록 페이지 (텍스트 입력)
- [x] AI 채팅 (WebSocket 스트리밍, Thinking 모드)
- [x] 민원 답변 초안 생성
- [x] 문서 검색 (키워드)
- [x] PII 스캔 / 마스킹
- [x] 문서 비교
- [x] 파일 관리
- [x] 초기 셋업 위저드
- [x] 시스템 트레이 런처 + 단일 인스턴스 보호
- [x] 브라우저 UI 종료 버튼 (`POST /api/quit`)
- [x] AI 채팅에 사용자 부서·담당자 정보 자동 주입
- [x] 설정 → 내 정보 탭 (부서명, 담당자 편집)
- [x] 회의록 STT (faster-whisper, 브라우저 녹음 + 파일 업로드)
- [x] 회의록 필드 버그 수정 (date alias, attendees 타입, summary 응답)
- [x] Inno Setup 자동 설치 (winget)
- [x] 빌드 시 실행 중인 앱 자동 종료 (`_kill_running_app`)
- [x] **절전 복귀 후 앱 영구 불능 버그 수정** — `SQLite busy_timeout=5000` + 시작 시 `wal_checkpoint(TRUNCATE)`로 잔여 WAL 파일 정리 (`database.py`)
- [x] **환경 감지 버그 수정** — `_detect_environment()`에서 삭제된 `laptop_high_ram` 프로필 반환 제거 → RAM ≥32 GB는 `desktop`, 미만은 `laptop` (`config.py`)
- [x] **법령검색 시드 데이터 구축** — 국가 법령 9종 38조문 (migrations 004~005) + 광명시 자치법규 6종 91조문 (migration 006, PyMuPDF PDF 추출), FTS5 전문 검색 적용
