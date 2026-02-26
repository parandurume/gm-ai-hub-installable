# UX Polish Designer — Agent Memory

## Project: GM-AI-Hub
Local-only desktop web app (Electron-free: FastAPI backend + React 18/Vite frontend) for
civil servants at 광명시청 (Gwangmyeong City Hall, South Korea).

## Design System Tokens
- Navy: #0F2040 (sidebar bg, dark text bg)
- Navy2: #1A3560 (sidebar hover)
- Teal: #007A5E (primary action, active nav)
- Teal2: #00A87A (brand accent, link hover)
- Amber: #D4860A (warning)
- Red: #C0392B (error, danger)
- Paper: #F7F5F0 (body bg)
- Paper2: #EDEAE3 (subtle bg)
- Ink: #1C1C22 / Ink2: #44444F / Ink3: #6B6B7D (text hierarchy)
- Border: #D8D5CC
- White: #FFFFFF
- Base font: Noto Sans KR, 14px
- Radius: 10px (cards), 6px (inputs/buttons)
- Shadow: 0 2px 12px rgba(15,32,64,0.10)
- Sidebar width: 220px (desktop), 64px (tablet <=1024px), overlay (mobile <=768px)
- Topbar height: 54px
- Content padding: 24px

## Navigation Items (current order — Sidebar.jsx groups)
Group "문서 작성": 기안문 작성 / 회의록 / 민원 답변
Group "검색 / 분석": 문서 검색 / 법령 검색 / PII 관리 / 문서 비교
Group "보조 도구": AI 채팅 / 문서 관리
Dashboard (home link, ungrouped) / 설정 (bottom, ungrouped)
NOTE: Sidebar groups already exist (added in v3.x). MEMORY was stale.

## Key Component Patterns
- Split-view layout (grid 1fr 1fr): GianmunPage, MeetingPage, ComplaintPage, SearchPage, DiffPage, FilesPage
- PII tri-view: 280px file list | flex-1 heatmap | 260px findings (collapses at <=1024px)
- Toast: ToastProvider context, auto-dismiss (success 3s, info 4s, warning 6s, error never). Has close button.
- ModelSelector: button-card pattern with keyboard support (focus-visible). Cached model list.
- ThinkingPanel: collapsible reasoning trace, streams live with pulse indicator
- GuardSummaryBar: chip row for date/PII/budget guard results after AI generation
- SetupWizard: 5 steps (welcome/ollama/models/info/ready), full page replacement, window.location.replace on complete

## Status: v3.4.0 Fixes Already Shipped (DO NOT re-recommend these)
- window.confirm() on ChatPage replaced with ConfirmModal (done)
- window.confirm() on FilesPage NOT yet replaced (still uses confirm())
- Sidebar navigation groups exist (문서 작성 / 검색 분석 / 보조 도구)
- ComplaintPage now has unified "AI 분석 및 답변 초안 작성" primary button + "분류만" secondary
- SettingsPage working_dir now uses FolderPicker pattern (save-path-row)
- MeetingPage: STT status endpoint exists, cached flag shows "~1.5GB 다운로드" warning but NO download progress modal on first record press — still a gap
- AttendeesTagInput component exists in MeetingPage (already built)
- GuardSummaryBar and AnnotatedPreview already shipped
- char counter already on body_instruction in GianmunPage and chat input

## Remaining Known Issues / UX Gaps (from v3.4.0 audit)
See: patterns.md for full detail
- AI SESSION FEEDBACK (user-reported, top priority): MeetingPage uses non-streaming POST for meeting generation — user sees only "AI 요약 중..." spinner with no token output, no phase labels, no ETA
- GianmunPage: generating state shows "AI 생성 중..." on button but preview pane shows nothing until first token — needs skeleton loader in right pane
- GianmunPage: no auto-scroll to preview pane after generation starts (user must look right)
- ChatPage: WebSocket reconnect silently on disconnect — no visual reconnection state indicator
- ChatPage: when isStreaming=true and text='', only shows "응답 준비 중..." but no elapsed-time counter (users think app froze)
- FilesPage: delete still uses window.confirm() — ConfirmModal not applied here
- DiffPage: no file type filter on selects; diff lacks line numbers
- Dashboard: no recent activity list; no quick-entry chat field
- SetupWizard: step dots have no text labels; can skip Ollama step without connecting
- All AI pages: no global "AI is busy" indicator in Topbar when any page's AI is running
- SampleManager: uses undeclared var(--bg2) CSS variable (should be var(--paper2))
- HwpxPreview: dangerouslySetInnerHTML used — OK for local content but needs note
- Error toast copy is generic (e.g., "처리 실패") — no actionable guidance
- No keyboard shortcut system; Tab navigation not verified on all interactive cards
- Topbar Ollama status only refreshes every 30s — stale state during active sessions
- MeetingPage: no streaming for AI generation (non-streaming postJSON) — blank wait period

## Primary Persona
김민준 (35M), 정보통신과 주무관, 5-year civil servant, comfortable with PC but not a developer.
Daily tasks: 기안문 2-3건/day, 회의록 1-2건/week, 민원 답변 3-5건/day, PII check before filing.
Pain: MS Office habits, time pressure from deadlines, fear of personal info leakage.

## Detailed Notes
See: patterns.md
