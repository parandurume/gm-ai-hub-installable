# GM-AI-Hub 개발 백로그

우선순위: 🔴 High / 🟡 Medium / 🔵 Low
상태: `[ ]` 미착수 / `[~]` 진행 중 / `[x]` 완료

---

## v3.x — 다음 릴리스

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
