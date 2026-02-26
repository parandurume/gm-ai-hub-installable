# GM-AI-Hub 개발 백로그

우선순위: 🔴 High / 🟡 Medium / 🔵 Low
상태: `[ ]` 미착수 / `[~]` 진행 중 / `[x]` 완료

---

## v3.x — 다음 릴리스

### UX 감사 — AI 세션 피드백 및 사용성 개선 (2026-02-27)

> UX 에이전트 전체 감사 결과. 현재 점수 7.0/10 → 목표 8.8/10.
> 핵심 문제: AI 세션 중 진행 상태 피드백 부재 ("화면이 깜깜하다")

#### Sprint 1 — Quick Wins (~2일)

- [ ] 🔴 **MeetingPage: AI 생성 중 피드백 없음** — `handleGenerate()`가 plain fetch로 15-60초 대기. 단계별 진행 표시(Phase labels) 추가 (`MeetingPage.jsx`)
- [ ] 🔴 **GianmunPage: 첫 토큰 전 빈 화면** — `generating=true && preview===''`일 때 skeleton loader 추가 (`GianmunPage.jsx`)
- [ ] 🔴 **ChatPage: 경과 시간 표시** — "응답 준비 중..." 상태에 elapsed timer 추가, 15초 후 힌트 표시 (`ChatPage.jsx`)
- [ ] 🟡 **FilesPage: `window.confirm()` → ConfirmModal** — ChatPage는 수정됨, FilesPage 미적용 (`FilesPage.jsx:34`)
- [ ] 🟡 **ChatPage: AI 메시지 복사 버튼** — assistant 메시지에 클립보드 복사 버튼 추가 (`ChatPage.jsx`)
- [ ] 🟡 **ComplaintPage: 글자 수 카운터** — 민원 내용 textarea에 3000자 제한 + 카운터 (`ComplaintPage.jsx`)
- [ ] 🟡 **에러 메시지 개선 (전체)** — 일반적 "실패" → 원인+해결 안내로 변경 (전체 페이지)
- [ ] 🟡 **SetupWizard: 레이블 스테퍼 + Ollama 연결 강제** — 단계 번호+이름 표시, 미연결 시 다음 단계 차단 (`SetupWizard.jsx`)
- [ ] 🔵 **SampleManager: `var(--bg2)` → `var(--paper2)`** — 미정의 CSS 변수 수정 (`SampleManager.jsx:351`)
- [ ] 🔵 **ThinkingPanel: 펼침/접힘 애니메이션** — CSS transition 추가 (`components.css`)
- [ ] 🔵 **Guard chip 등장 애니메이션** — fade+scale stagger 효과 (`components.css`)

#### Sprint 2 — Core Improvements (~1주)

- [ ] 🔴 **Topbar: 글로벌 AI-Busy 표시** — AiBusyContext 생성, 페이지 이동 시에도 AI 처리 중 표시 (`Topbar.jsx`, `App.jsx`)
- [ ] 🔴 **MeetingPage: SSE 스트리밍 전환** — GianmunPage와 동일한 스트리밍 패턴으로 전환 (backend + `MeetingPage.jsx`)
- [ ] 🟡 **Dashboard: 최근 작업 목록** — 최근 문서 10개 표시 (`Dashboard.jsx`)
- [ ] 🟡 **DiffPage: 줄 번호 + 변경 요약** — 비개발자 가독성 향상 (`DiffPage.jsx`)
- [ ] 🟡 **Topbar: Ollama 폴링 주기 단축** — 30초 → 10초, AI 에러 시 즉시 재확인 (`Topbar.jsx`)

#### Strategic Enhancements (향후)

- [ ] 🟡 **법령검색 → AI 채팅 연결** — 조문에 "AI에게 물어보기" 버튼, ChatPage로 이동 + 프롬프트 자동 입력
- [ ] 🟡 **GianmunPage: 인라인 미리보기 편집** — preview pane에 편집 모드 토글
- [ ] 🟡 **PII 검사 보고서 내보내기** — HWPX 형식 감사 기록 생성
- [ ] 🟡 **SetupWizard: 인앱 모델 다운로드** — step 3에서 SSE pull-stream으로 모델 다운로드

### STT / 회의록

- [ ] 🔴 **STT PyInstaller 패키징** — `faster_whisper`, `ctranslate2` hidden imports를 `build/gm-ai-hub.spec`에 추가하고 `.pyd`/`.dll` 바이너리 포함 확인
- [ ] 🔴 **STT 모델 첫 실행 UX** — 첫 음성 인식 시 모델 다운로드(~1.5 GB)가 시작됨. 설정 페이지에 "STT 모델 다운로드" 버튼 + 진행률 표시 추가
- [ ] 🟡 **실시간 스트리밍 STT** — 녹음 중 WebSocket으로 부분 텍스트를 실시간으로 textarea에 반영 (faster-whisper VAD 기반 청킹)
- [ ] 🟡 **STT 모델 설정** — 설정 페이지에서 tiny/base/small/medium/large-v3 모델 선택 옵션 추가
- [ ] 🔵 **회의록 화자 분리** — 발화자별 텍스트 구분 (pyannote.audio + faster-whisper 조합, GPU 필요)

### AI 기능

- [ ] 🔴 **HyperCLOVA X OmniServe 연동** — NAVER Cloud OmniServe API(OpenAI 호환) 옵션 추가. `backend/ai/client.py`에 provider 선택 로직 구현. 인터넷 연결 시 사용 가능한 고성능 한국어 모델.
- [ ] 🟡 **기안문 작성에 내 정보 자동 입력** — `department_name` / `officer_name`을 기안문 폼의 부서명·작성자 필드 기본값으로 설정
- [ ] 🟡 **민원 답변에 내 정보 반영** — 답변 초안 서명란에 부서명·담당자 자동 삽입
- [ ] 🟡 **AI 채팅 히스토리 저장** — SQLite에 대화 이력 저장 및 불러오기
- [ ] 🔵 **RAG 개선** — nomic-embed-text 임베딩 기반 문서 검색을 벡터 DB(ChromaDB)로 전환

### 설정 / UX

- [ ] 🟡 **STT 언어 설정** — 설정 페이지에서 음성 인식 언어 선택 (ko/en/auto)
- [x] 🟡 **작업 폴더 선택 다이얼로그** — FolderPicker 컴포넌트로 교체 (설정 > 일반 탭)
- [ ] 🔵 **다크 모드** — CSS 변수 기반 테마 토글
- [ ] 🔵 **앱 자동 업데이트** — 버전 체크 + 새 인스톨러 다운로드 알림

### 빌드 / 배포

- [ ] 🔴 **v3.2.0 재빌드 및 재설치** — 절전 버그 수정 + 환경 감지 수정 + 법령검색 데이터(006) 반영을 위해 `python build/build.py` 실행 후 인스톨러 재배포 필요
- [ ] 🔴 **PyInstaller spec 업데이트** — faster-whisper 추가에 따른 hidden imports:

  ```python
  hiddenimports=['faster_whisper', 'ctranslate2', 'huggingface_hub']
  ```

  ctranslate2 `.dll` 파일을 `binaries` 섹션에 포함해야 할 수 있음
- [ ] 🟡 **인스톨러 버전 동기화** — `pyproject.toml` version과 `installer/gm-ai-hub.iss` version을 빌드 시 자동으로 동기화
- [ ] 🟡 **코드 서명** — Windows Defender 경고 방지를 위한 EV 코드 서명 인증서 적용
- [ ] 🔵 **자동 빌드 CI** — GitHub Actions 또는 로컬 스케줄러로 정기 빌드 자동화

### 보안 / 안정성

- [ ] 🟡 **PII 검사 회의록 적용** — STT 변환 결과에 자동 PII 스캔 후 사용자에게 경고
- [ ] 🟡 **API 인증** — 로컬호스트 전용이지만 CSRF 토큰 또는 Origin 헤더 검증 추가
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
