# GM-AI-Hub UX Patterns & Audit Notes

## Architecture Context
- React 18 + Vite SPA loaded in a browser window (no Electron; system tray launcher opens Chrome/Edge)
- FastAPI backend at localhost:8080, WebSocket for chat streaming, SSE for gianmun AI body generation
- All AI runs via Ollama (local). No cloud calls except optional HyperCLOVA X (backlog).
- HWPX output via custom hwpx_service (no LibreOffice dependency for write; pyhwp for read)
- SQLite DB for settings, documents index, chat history (future)

## Component-Level Observations

### GianmunPage
- Split layout: left=form, right=preview
- SSE stream for AI body generation (not WebSocket)
- Auto-validates after stream completes (date guard, PII, budget)
- GuardSummaryBar shows chips per guard status
- AnnotatedPreview shows inline colored underlines for flagged spans
- FolderPicker component embedded for save path
- MISSING: character count on body_instruction textarea
- MISSING: auto-scroll to preview pane after generation completes
- MISSING: ability to edit the AI preview inline before saving
- MISSING: loading skeleton in preview pane during stream

### MeetingPage
- Split layout: left=form+STT controls, right=result
- STT: MediaRecorder → webm blob → POST /api/meeting/transcribe
- Timer shows MM:SS during recording with red dot indicator
- MISSING: STT model download progress UI (first-run ~1.5 GB download)
- MISSING: streaming STT output during recording
- MISSING: attendees field accepts comma-separated text — consider tag chips
- NOTE: meeting/create is NOT streaming, unlike gianmun. User sees loading spinner then full result.

### ChatPage
- WebSocket streaming with useWebSocket hook
- Thinking panel collapsible per message
- Example prompts clickable chips on empty state — good pattern
- Uses window.confirm() for 대화 초기화 — MUST replace with modal
- MISSING: character count on input textarea
- MISSING: chat history persistence (backlog)
- MISSING: copy-to-clipboard button on AI messages
- Deep mode adds multi-step clarification flow via system prompt injection
- Reasoning slider is actually 3 toggle buttons (간결/보통/상세), not an actual range slider

### ComplaintPage
- Two separate API calls (분류 then 초안) — creates cognitive friction
- Classification result shown in the left panel — good
- MISSING: combined "분류 + 초안 한 번에" primary action
- MISSING: edit handle on draft before saving

### PiiPage
- Tri-view: file list | heatmap preview | findings list
- Cross-highlights between heatmap and findings list (hover sync)
- PII type color coding is consistent across both panels
- MISSING: export findings as report (CSV/PDF)
- MISSING: PII scan on STT transcription output (backlog)

### SearchPage
- Hybrid/keyword/semantic search mode selector
- Results in table with score and snippet
- HwpxPreview on the right when a result is selected
- MISSING: search history
- MISSING: highlight search terms in the preview pane

### SettingsPage
- URL-linked tabs via ?tab= param (already implemented)
- Profile tab: only department_name and officer_name
- General tab: working_dir is raw text (should use FolderPicker), ollama_url, pii_scan_on_export
- Models tab: read-only table; no install/pull button
- Optimization tab: pipeline-specific optimize buttons (gianmun/docent/complaint/meeting)
- Samples tab: SampleManager component

### SetupWizard
- 5 steps with dot progress indicator
- Missing: visual step labels (just dots, no text)
- Missing: step-level validation before allowing Next (can skip Ollama setup)
- Ollama connection check auto-triggers on step entry
- window.location.replace('/') used instead of navigate() to force SetupGuard re-check

### Dashboard
- 4 cards: system status, AI engine, prompt optimization, quick links
- Quick links: only 4 items hardcoded (기안문, 문서 검색, AI 채팅, PII 검사)
- MISSING: recently-used items
- MISSING: today's document count or activity summary
- MISSING: AI engine model name prominently shown
- MISSING: actionable CTA when Ollama is offline

### Topbar
- Shows current page title (Korean)
- Ollama status pill (online/offline with color dot) — polls every 30s
- Quit button (power icon)
- Hamburger hidden unless <=768px

### Sidebar
- memo'd component — good
- NavLink with `end` on home route
- Footer shows version number
- No section groupings for 11 items — becomes a long flat list

## Layout System Issues
- content area has `max-width: 1400px` but no `margin: 0 auto` — left-aligned on ultrawide
- split-view height: calc(100vh - topbar - 48px) — may clip on laptops with small screens
- PII tri-view minimum 280+1fr+260 = very tight below 1100px; tablet breakpoint collapses to 2-col but the 2-col layout isn't well specified

## Accessibility Notes
- model-card buttons: have focus-visible outline (good)
- thinking-toggle button: has focus-visible (good)
- Toast: has role="status" aria-live="polite" (good)
- hamburger button: has aria-label (good)
- quit button: has aria-label (good)
- MISSING: skip-to-content link
- MISSING: ARIA landmarks on main regions (nav, main, header)
- MISSING: form labels not explicitly associated to inputs in some places (use htmlFor)
- MISSING: focus trap in modals (FolderPicker)
- Color contrast: ink3 (#6B6B7D) on white fails WCAG AA for body text (4.0:1, need 4.5:1)
- Ink3 is used for form labels — these are secondary labels so borderline acceptable, but worth checking

## Toast System
- DISMISS_MS: success=3s, info=4s, warning=6s, error=never (manual close required)
- Close button present and working
- Role and aria-live set correctly
- Stacks vertically at top-right

## Navigation IA Recommendation
Current order doesn't match task frequency. Proposed reorder:
1. 대시보드
2. 기안문 작성 (most frequent primary task)
3. 회의록 (second most frequent)
4. 민원 답변 (daily task)
5. AI 채팅 (utility, cross-task)
6. --- separator: 문서 도구 ---
7. 문서 검색
8. 법령 검색
9. PII 관리
10. 문서 비교
11. 문서 관리
12. --- separator: 시스템 ---
13. 설정

## Design Tokens Used in Components
- `var(--line)` referenced in FilesPage but NOT defined in global.css — likely a bug (should be --border)
- `var(--bg-secondary)` referenced in components.css .fetching-status but not defined — likely should be --paper
- `var(--bg)` referenced in chat-fetched-urls but not defined
