# GM-AI-Hub — Comprehensive User Story & UX Redesign Vision
**Version 1.0 — February 2026**

---

## UX Audit Summary

GM-AI-Hub is a technically sound, privacy-first AI desktop tool built for a very specific user: a Korean municipal civil servant who writes official documents every day. The core value proposition — local AI that never sends data to the cloud — is strong and correctly positioned.

The current v2.x experience is functional but was clearly built feature-first. The result is a well-engineered product that still feels like a developer prototype: navigation ordering does not reflect actual task frequency, empty states are generic, several critical confirmation dialogs use browser `window.confirm()` (which is visually jarring and cannot be styled), there is no activity continuity across sessions, and the Dashboard offers no actionable information beyond system status. The app's 11-item flat navigation list has no grouping, making cognitive load higher than it needs to be.

The design system itself is coherent and well-chosen. The color palette (navy/teal/amber/paper) is professional and government-appropriate. The split-view layout pattern is the right choice for document workflows. These are strengths to build on, not replace.

The fundamental upgrade needed is not a visual redesign — it is a **workflow coherence upgrade**: make the app understand that the user has a job to complete, sequence the UI to match that job, and eliminate the friction points that force the user to think about the tool instead of the work.

**Current experience quality: 6.5/10**
**Target after recommended improvements: 8.5/10**

---

## Part 1: User Personas

### Primary Persona — 김민준 (Kim Min-jun)

**Role:** 주무관 (General Affairs Officer), 5th year
**Department:** 정보통신과 (IT & Communications Division)
**Age:** 35
**Technical proficiency:** Comfortable with Windows PC, Microsoft Word/Excel, government intranet. Has used ChatGPT casually. Not a developer.

**Daily work context:**
- Writes 2-3 기안문 per day (budget requests, project proposals, policy submissions)
- Attends 1-2 meetings per week; must produce a formatted 회의록 within 24 hours
- Handles 3-5 민원 (citizen complaints/requests) per day; each requires a formal written response
- Must check all outgoing documents for personal information (PII) — this is legally mandated
- Works on a government-issued Windows 10 PC with 16 GB RAM; internet access is restricted on certain networks
- Uses 한글(HWP/HWPX) exclusively — MS Word is not an option in Korean government

**Goals:**
1. Complete a 기안문 in under 10 minutes (currently takes 25-40 minutes)
2. Never accidentally leak a citizen's personal information in an outgoing document
3. Have a draft 회의록 ready before leaving the meeting room
4. Not have to learn a new complicated tool — it should work like a smart assistant, not a software product

**Frustrations:**
- Blank-page paralysis: starting a formal document from zero is mentally exhausting
- PII anxiety: manually reading through long documents to find phone numbers and IDs is error-prone and stressful
- Meeting notes chaos: scribbled notes + recorded audio → needs to be a formatted document in 30 minutes
- Repetitive boilerplate: writing the same department/date/reference number header on every document
- Fear of AI: worried about data going to the cloud; wants assurance that the system is private

**Emotional relationship with the tool:**
Min-jun should feel *relief* when he opens GM-AI-Hub — like having a competent colleague who handles the tedious parts of his job. He should never feel confused, never feel uncertain about what the AI did to his document, and never feel exposed or at risk.

---

### Secondary Persona — 이수연 (Lee Su-yeon)

**Role:** 팀장 (Section Chief), 12th year
**Department:** 복지정책과 (Welfare Policy Division)
**Age:** 43
**Technical proficiency:** Comfortable with government systems; cautious about AI tools; approves documents written by juniors

**Context:** Su-yeon reviews documents that juniors produce with GM-AI-Hub. She uses the tool herself mainly for:
- Reviewing AI-generated documents with the 문서 비교 tool (comparing draft vs. final)
- Running PII scans on batches of citizen-related documents before quarterly archiving
- Occasionally using AI 채팅 to ask policy-related questions

**Goals:**
1. Trust the output — she needs to know what the AI changed vs. what the original said
2. Batch-process compliance (PII scan on 20-30 documents at once)
3. Be confident the tool is not sending citizen data anywhere

**Frustrations:**
- Batch PII scan exists but the results are not exportable as a report
- Document diff output is raw unified diff format — not readable for a non-developer
- She cannot tell at a glance which documents were AI-assisted vs. human-written

---

### Tertiary Persona — 박정호 (Park Jeong-ho)

**Role:** 정보화 담당 (IT Administrator), 8th year
**Department:** 정보통신과
**Age:** 38
**Technical proficiency:** Power user, manages the city's internal PC infrastructure

**Context:** Responsible for deploying and maintaining GM-AI-Hub across the organization. Uses Settings, monitors the Ollama health status, manages model updates, and runs prompt optimization after training sample collection.

**Goals:**
1. One-click deployment via the Inno Setup installer
2. Clear health status at a glance (is Ollama running? which models are loaded?)
3. Be able to run MIPROv2 prompt optimization without understanding ML

**Frustrations:**
- Settings page doesn't show which model is currently active for which task
- Prompt optimization button labels are internal pipeline names (gianmun/docent/complaint/meeting) — not readable by a non-developer
- No audit log viewer in the UI (exists in backend but not exposed)
- STT model download (~1.5 GB) can trigger silently on first use — needs progress UI

---

## Part 2: Core User Journeys (Jobs-to-be-Done Framework)

---

### Journey 1: 기안문 작성 (Official Document Drafting)

**Job statement:** "When I need to write an official document, I want to produce a correctly formatted, reviewed draft in under 10 minutes, so I can meet my submission deadline and not worry about mistakes."

**Current flow (as-is):**

1. User navigates to sidebar → 기안문 작성 (third item, one click)
2. Selects template type from dropdown (no preview of what each template produces)
3. Types a subject/title
4. Optionally types body instructions in the textarea (no character counter, no guidance on what good instructions look like)
5. Optionally selects an AI model (auto-select is fine; model cards are small and technical)
6. Optionally picks a save path via FolderPicker
7. Clicks "AI 본문 생성" — streaming begins
8. Preview panel shows streaming text with a blinking cursor
9. ThinkingPanel shows collapsible reasoning (good UX)
10. After stream completes, GuardSummaryBar shows date/PII/budget chips
11. AnnotatedPreview shows inline color underlines for flagged spans
12. User reads the preview and decides to save
13. Clicks "HWPX 저장" — file saved to configured path

**Friction points in current flow:**
- The form feels like a generic web form, not a document tool — the split view helps, but the left panel has no visual hierarchy to guide the user
- There is no example text in the body_instruction placeholder beyond a single sentence
- After generation completes, the user's eye needs to travel from the left panel (where the buttons are) to the right panel (where the preview is) — no auto-scroll on mobile/tablet
- The save path uses a monospace path string that looks technical; most users won't change it
- After saving, there is no "open in 한글" shortcut or "share this document" action
- The AnnotatedPreview is powerful but users don't know what the colors mean without hovering
- A legend for guard annotation colors is absent

**Ideal flow (to-be):**

1. User opens the app. Dashboard shows "기안문 시작" as the primary CTA (large, prominent).
2. User clicks it. A **document type selector** appears as visual cards with icons and descriptions (not a raw dropdown): "일반기안", "협조전", "보고서", "민원답변", "계획서" — each with a one-line description of when to use it.
3. User picks a type. The form collapses to show only the fields relevant to that type.
4. Subject field is focused automatically. A "제목 예시 보기" link reveals 3 example titles for context.
5. Body instructions field has a character counter (0/500) and a collapsible "좋은 지시사항 작성 팁" section.
6. User types subject and optional instructions; clicks "AI 생성" (renamed from "AI 본문 생성" — shorter, clearer).
7. The right panel immediately shows a **skeleton loading state** (3 grey paragraph-height bars pulsing) before the first token arrives — perceived performance improvement.
8. Streaming text fills in, replacing the skeleton.
9. After completion, the guard chips animate in. A color legend appears inline: "● 날짜 확인 필요  ● 개인정보 포함  ● 예산 언급."
10. A **"수정하기"** button enables inline editing of the preview text in place.
11. Save button is renamed "HWPX로 저장하기" and placed as a full-width primary button below the preview when ready — the user's eye naturally arrives there after reading.
12. Success state: toast + a **"저장된 파일 열기"** link (opens the file folder in Windows Explorer).

---

### Journey 2: 회의록 작성 (Meeting Minutes)

**Job statement:** "When a meeting ends, I want to turn my notes or recording into a formatted official meeting minutes document before I leave the building, so I can submit it to my supervisor on time."

**Current flow (as-is):**
1. Navigate to sidebar → 회의록 (6th item — requires scrolling on smaller screens)
2. Fill in title, date (pre-filled with today), attendees (comma-separated text field)
3. Choose between 녹음 (microphone) or 파일 (audio file upload) for STT, OR type manually
4. Click 녹음 — recording starts; MM:SS timer shows in red
5. Click 중지 — recording stops; STT transcription sends to backend
6. First time: Whisper model download (1.5 GB) begins silently — the user sees "음성 인식 중..." indefinitely
7. Transcribed text appears in the textarea; user can edit
8. Click "AI 회의록 생성" — non-streaming POST; spinner shows while backend processes
9. Right panel shows the formatted meeting minutes
10. File is auto-saved to the configured working directory

**Critical friction points:**
- The STT model download (~1.5 GB) is completely silent in the current UI — the user has no idea why it seems frozen. This is the #1 first-run failure point.
- The attendees field is a plain comma-separated text input — no validation or tag UI
- There is no way to review/edit the transcribed text and then re-generate without clearing everything
- The generated result is non-streaming (user waits with a spinner)
- No ability to add items like 결정사항 or 후속조치 from the front-end form (backend supports these fields but the frontend form does not expose them)
- If the user forgets to fill in the title before clicking generate, they get an error toast and lose focus

**Ideal flow (to-be):**
1. Navigation item moves to 2nd position (after 기안문 — high daily frequency).
2. On first STT use, before the recording starts: a **STT 모델 준비** interstitial appears with a progress bar and "최초 실행 시 AI 음성인식 모델 다운로드가 필요합니다 (~1.5 GB). 잠시 기다려 주세요." — converts confusion to expectation.
3. Recording UI is upgraded: a **waveform visualizer** (simple canvas animation) gives live audio feedback; the red timer is kept.
4. Attendees field becomes a **tag input** — user types a name and presses Enter or comma to add a chip. Chips are removable.
5. After transcription, the textarea shows the text with a "편집 완료" button — a subtle reminder that the user can edit before generating.
6. Clicking "AI 회의록 생성" starts **streaming output** (matching the gianmun pattern) — no more waiting blindly.
7. The result panel adds expandable sections: "결정사항" and "후속조치" — pre-filled if AI detected them, editable.
8. HWPX save auto-names the file as `회의록_[title]_[YYYYMMDD].hwpx` and shows the final path.

---

### Journey 3: 민원 답변 (Citizen Complaint Response)

**Job statement:** "When a citizen submits a complaint, I want to classify it correctly and produce a professionally worded formal response draft in under 3 minutes, so I can handle my daily complaint load without burnout."

**Current flow (as-is):**
1. Navigate to complaint page
2. Paste the citizen's complaint text into the textarea
3. Click "민원 분류" → small classification card appears (category, department, urgency)
4. Click "AI 답변 초안" → right panel shows the draft response
5. Two separate API calls = two button clicks = awkward

**Friction points:**
- Two buttons for a logically sequential task creates decision fatigue: "do I need to classify first? can I skip classification?"
- The draft response appears in a read-only preview pane — no way to edit inline
- No copy-to-clipboard on the draft
- No way to quickly insert the user's department/name into the response (backlog item)
- The "민원 내용" textarea has no character counter; complaints can be very long

**Ideal flow (to-be):**
1. The page opens with a single large textarea prominently labeled "민원 내용 붙여넣기." A char counter is visible (0 chars).
2. User pastes text. A single primary button: "AI 분석 및 답변 초안 작성" — this triggers classification AND draft generation in one step. Classification happens in the background; the draft streams into the right panel.
3. Classification badge appears above the draft result (category chip + urgency indicator).
4. The draft response is **editable inline** — clicking the text enables editing directly.
5. A "복사하기" (Copy) button appears below the draft for pasting into the government intranet system.
6. A secondary "HWPX 저장" button saves the draft as a file.
7. The user's department/name from Settings is automatically appended to the closing of the draft.

---

### Journey 4: AI 채팅 (AI Chat / General Assistant)

**Job statement:** "When I have a question about policy, law, or document writing that doesn't fit a specific template, I want to ask in natural Korean and get a helpful, accurate answer I can trust."

**Current flow (as-is):**
1. Navigate to AI 채팅 (5th in navigation)
2. See empty state with example prompts — good UX
3. Type in the textarea (auto-expands); Enter to send, Shift+Enter for newline
4. WebSocket streams the response; ThinkingPanel shows if reasoning model is used
5. Config bar at top: reasoning level (3 toggle buttons), deep mode toggle, model selector
6. "대화 초기화" uses `window.confirm()` — browser native dialog
7. Chat history is session-only (not persisted)

**Friction points:**
- The config bar at the top (reasoning level + deep mode + model) is shown even to users who don't need it — adds cognitive load for simple use cases; should be collapsed/secondary by default
- `window.confirm()` for 대화 초기화 is inconsistent with the rest of the design system (should be a styled modal)
- No character counter on the input textarea
- No message copy button on AI responses
- Chat history is lost on page refresh or navigation — high frustration for long research sessions
- The reasoning toggle labels "간결/보통/상세" are ambiguous — don't explain the tradeoff (speed vs. depth)
- "Deep mode" label is too technical; many users won't understand what it does

**Ideal flow (to-be):**
1. Chat input occupies the full attention of the page. Config options moved to a **collapsed gear icon** in the input area — advanced users expand it, casual users never see it.
2. Reasoning level renamed and explained:
   - 간결 → "빠른 답변" (faster, shorter)
   - 보통 → "균형" (balanced — default)
   - 상세 → "깊은 분석" (slower, more thorough with reasoning trace)
3. Deep Mode renamed "단계별 분석" with a tooltip: "AI가 답변 전 추가 질문을 해서 더 정확한 답변을 제공합니다."
4. Add char counter below textarea.
5. Add copy icon button on each AI message bubble.
6. Implement **chat session persistence** in SQLite (already in backlog): show a sidebar or dropdown "이전 대화 불러오기."
7. 대화 초기화 triggers a styled modal: "대화 내용이 모두 삭제됩니다. 저장되지 않은 내용은 복구할 수 없습니다. [취소] [삭제하기]"

---

### Journey 5: PII 검사 및 마스킹 (Personal Information Scan)

**Job statement:** "Before I submit or archive a document, I need to verify it doesn't contain any personal information that shouldn't be there, and mask anything that should be redacted, so I comply with the Personal Information Protection Act."

**Current flow (as-is):**
1. Navigate to PII 관리 (9th item — far down the navigation)
2. Tri-view layout: left=file list, center=heatmap, right=findings
3. Select a file → click "PII 스캔" → heatmap shows colored underlines; findings list on right
4. Click a finding row → corresponding highlight becomes active in heatmap
5. Click "PII 마스킹" → saves a new masked version of the file
6. "일괄 스캔" button scans all files → summary chips show totals per type

**Friction points:**
- PII 관리 is the 9th navigation item despite being a daily compliance requirement
- The batch scan result shows totals per type but no per-file breakdown (which files had what)
- No ability to export the scan result as a report (PDF/CSV) for compliance documentation
- Heatmap center panel has no loading skeleton — just empty white space while scanning
- Findings list shows character position (`:1234`) which is meaningless to end users — should show the matched value (redacted if sensitive) and surrounding context
- Masking creates a new file but does not tell the user the new file's name/path in a clear way

**Ideal flow (to-be):**
1. Navigation item moved up to position 7 (within the "document tools" group).
2. PII scan is also offered as a **quick action on the GianmunPage** after AI generation (guard chip is already there — clicking it should open a mini PII view for that document specifically).
3. Batch scan result is presented as a **table**: one row per file, color-coded PII type columns, with a drill-down to open that file in the full PII view.
4. Findings list shows: type chip + matched value (partially masked, e.g., "홍**동") + context snippet (5 words before/after).
5. "내보내기" button generates a compliance report HWPX listing all findings.
6. After masking, the toast includes the new file name as a link/path.

---

### Journey 6: Setup (First-Run Experience)

**Job statement:** "When I install GM-AI-Hub for the first time, I want to be running and productive within 10 minutes, without needing to contact IT support."

**Current flow (as-is):**
1. Setup wizard: 5 steps (welcome/ollama/models/info/ready)
2. Progress indicated by dots — no step labels
3. Can advance past Ollama step even if Ollama is not connected
4. Model install requires terminal command (`ollama pull ...`) — no UI download
5. The "시작하기" button on the ready step reloads the whole page (workaround for SetupGuard)

**Friction points:**
- Step dots have no labels — user doesn't know how many steps are left or what each step is
- Can skip past a broken Ollama connection — will cause all AI features to fail silently later
- Model install via terminal is a barrier for non-technical users
- No "완료" animation or welcome moment — just hard page redirect
- Step 3 (models) shows recommended models but no "모델 다운로드" button — just a code string to copy

**Ideal flow (to-be):**
1. Dots replaced with **labeled stepper**: "시작 > AI 엔진 > 모델 > 내 정보 > 완료"
2. The Next button is disabled with a tooltip explanation if Ollama is not connected: "다음 단계로 가려면 Ollama 연결이 필요합니다."
3. Model step includes an in-app "다운로드 시작" button per missing model with a progress bar below (triggers `ollama pull` via backend API).
4. Also include STT model download option with size warning (~1.5 GB).
5. Ready step shows a short animation (teal checkmark expanding) and "시작하기" is styled as a celebration button, not just a plain form submit.

---

## Part 3: Navigation & Information Architecture Redesign

### Current Problems
- 11 flat items with no grouping
- Order does not reflect actual task frequency
- "문서 관리" (file browser) is item 2 — too prominent for an administrative utility
- "문서 비교" and "법령 검색" are specialty tools used occasionally — same visual weight as primary tasks

### Proposed Navigation Structure

**Group 1 — 주요 업무 (Core Tasks)**
```
대시보드
기안문 작성      ← was #3, move to #2
회의록           ← was #6, move to #3
민원 답변        ← was #7, move to #4
AI 채팅          ← was #5, move to #5 (unchanged in group)
```

**Group 2 — 문서 도구 (Document Tools)**
```
[구분선]
문서 검색
법령 검색
PII 관리
문서 비교
문서 관리
```

**Group 3 — 시스템 (System)**
```
[구분선]
설정
```

**Implementation:** Add a `group` property to NAV_ITEMS array; render a `<div class="nav-group-label">` separator when group changes. Section labels visible at desktop width; hidden (show only icon) at tablet width.

---

## Part 4: Dashboard Redesign Concept

### Current Dashboard Deficiencies
- Shows only static system status (server OK, Ollama OK, prompt optimization status)
- 4 quick link buttons that duplicate the sidebar
- No activity, no context, no recency

### Redesigned Dashboard: "오늘의 업무 현황" (Today's Work Status)

**Layout: 3-zone design**

**Zone 1 — System Status Bar (compact, top of page)**
A single horizontal bar replacing the current 3-card status grid:
```
[● Ollama 연결됨  gpt-oss:20b 사용 중]  [문서 7개]  [마지막 최적화: 3일 전]  [▲ v2.4.0]
```
This is informational context, not the primary content. Make it small and readable, not four large cards.

**Zone 2 — Primary Actions: "무엇을 도와드릴까요?" (Hero zone)**
3 large action cards, visually prominent:

```
[ 기안문 작성    ]  [ 회의록 작성   ]  [ 민원 답변    ]
[ ✍️ 새 문서 시작 ]  [ 📋 회의 내용 입력]  [ 📨 민원 붙여넣기]
```

Each card has:
- Icon (larger, 2rem)
- Title
- Short description (1 line)
- CTA button (links to the respective page)
- Estimated time: "약 5분" / "약 3분"

**Zone 3 — 최근 작업 (Recent Activity)**
A simple chronological list of recent documents/actions:
```
오늘  회의록_AI추진회의_20260224.hwpx  —  [열기]
어제  기안문_2026년사업계획.hwpx      —  [열기]
어제  민원답변_환경민원_홍길동.hwpx    —  [열기]  [PII재검사]
```
- Pulls from the documents index (already stored in SQLite)
- PII status indicator per document (clean / has findings / not scanned)
- "열기" opens the file folder in Windows Explorer

**Zone 4 — AI 채팅 Quick Entry (bottom, optional)**
A single-line "AI에게 질문하기..." input that navigates to the Chat page with the pre-filled query.

---

## Part 5: Critical UX Issues — Prioritized Fix List

### Priority 1 — Must Fix (blocks trust / causes data loss risk)

**P1-A: STT 모델 다운로드 UX**
- Where: MeetingPage, backend/services/stt_service.py
- Problem: First STT use triggers ~1.5 GB download with no user-visible progress
- Fix: Add `GET /api/meeting/stt-status` endpoint returning `{ ready: bool, downloading: bool, progress: float }`. Show pre-recording modal if not ready. Add "STT 모델 다운로드" button in Settings → 모델 관리 tab.
- Effort: 2 days
- Impact: Eliminates #1 first-run failure point

**P1-B: Replace window.confirm() with Modal**
- Where: ChatPage `handleClear()`, FilesPage `handleDelete()`, and the quit confirmation in Topbar `handleQuit()`
- Problem: Browser native dialog is unstyled, jarring, and inconsistent with the design system
- Fix: Create a `ConfirmModal` component using the existing `.modal` CSS classes. Props: `title`, `message`, `confirmLabel`, `onConfirm`, `onCancel`. Replace all three window.confirm() calls.
- Effort: 0.5 days
- Impact: Visual consistency, trust signal

**P1-C: Undefined CSS Variables**
- Where: FilesPage uses `var(--line)`, components.css uses `var(--bg-secondary)` and `var(--bg)` — none defined in global.css
- Fix: Add aliases in global.css:
  ```css
  --line: var(--border);
  --bg: var(--paper);
  --bg-secondary: var(--paper);
  ```
- Effort: 15 minutes
- Impact: Prevents potential invisible borders/backgrounds on some elements

**P1-D: Ink3 Color Contrast**
- Where: Form labels, secondary text, empty state text
- Problem: `--ink3` (#6B6B7D) on white (#FFFFFF) = ~4.0:1 contrast ratio. WCAG AA requires 4.5:1 for normal text.
- Fix: Darken ink3 to `#5E5E6E` (≈4.6:1) or reserve it only for decorative text; use `--ink2` for form labels.
- Effort: 30 minutes (token change + audit)
- Impact: Accessibility compliance

---

### Priority 2 — High Impact UX Improvements

**P2-A: Body Instruction Character Counter (기안문)**
- Where: GianmunPage, `form.body_instruction` textarea
- Fix: Add `<span class="char-counter">{form.body_instruction.length} / 500</span>` below the textarea, styled with `.form-group-footer { text-align: right; font-size: 0.75rem; color: var(--ink3); }`. Turn amber at 80%, red at 100%.
- Effort: 1 hour
- Impact: Reduces user uncertainty about input length

**P2-B: Chat Input Character Counter**
- Where: ChatPage, input textarea
- Fix: Same pattern as P2-A. Display below the input bar.
- Effort: 1 hour

**P2-C: Gianmun Document Type Selector (Visual Cards)**
- Where: GianmunPage, template dropdown
- Problem: A `<select>` dropdown gives no context about what each template produces
- Fix: Replace the `<select>` with a horizontally scrollable card row (similar to ModelSelector pattern). Each card: icon + type name + 1-line description. Collapses to a dropdown on mobile (reuse `<select>` with media query swap).
- Effort: 1 day
- Impact: Reduces incorrect template selection; speeds up first step of the flow

**P2-D: Navigation Grouping**
- Where: Sidebar.jsx, layout.css
- Fix: Add group separator dividers between task groups as described in Part 3. Add `.nav-separator { margin: 8px 12px; border-top: 1px solid rgba(255,255,255,0.1); }` and `.nav-group-label { padding: 4px 16px 2px; font-size: 0.68rem; font-weight: 600; color: rgba(255,255,255,0.35); text-transform: uppercase; letter-spacing: 0.05em; }`. Hidden on tablet (icon-only mode).
- Effort: 2 hours
- Impact: Reduces cognitive load; makes navigation scannable

**P2-E: Dashboard Redesign (Zones 1+2)**
- Where: Dashboard.jsx, components.css
- Fix: Implement the 3-zone redesign described in Part 4. Phase 1: system status bar (compact) + 3 primary action cards. Phase 2: recent activity list (requires documents API query by date).
- Effort: 2-3 days
- Impact: Transforms the dashboard from a status page into a launchpad; dramatically improves first impression

**P2-F: Settings Working Directory — FolderPicker**
- Where: SettingsPage, general tab
- Problem: `working_dir` is a raw text input. FolderPicker component already exists.
- Fix: Replace the text input with a save-path-row pattern using FolderPicker, identical to the pattern already in GianmunPage.
- Effort: 1 hour
- Impact: Usability; avoids typos in file paths

**P2-G: Complaint Page — Unified AI Action**
- Where: ComplaintPage
- Fix: Keep both buttons but make "AI 분류 + 답변 초안" the PRIMARY button (btn-primary) and "민원 분류만" a secondary button. Classification result populates automatically above the draft. Trigger classification and draft in a sequential chain on the primary button click.
- Effort: 3 hours
- Impact: Reduces confusion; matches user mental model (one job = one click)

**P2-H: Findings List — Human-Readable Context**
- Where: PiiPage, findings list (right panel)
- Problem: Findings show type + character position (`:1234`), which is meaningless
- Fix: Backend already returns `start`/`end` indices and the full text. Extract a context snippet: `text.slice(max(0, f.start-20), f.end+20)` and bold/highlight the matched portion. Show as: `[전화번호]  ...에게 연락처는 **010-XXXX-XXXX** 입니다.`
- Effort: half day (frontend only)
- Impact: Findings become immediately actionable; user understands what was found without reading the document

---

### Priority 3 — Strategic Enhancements

**P3-A: Chat History Persistence**
- Already in backlog (SQLite)
- Implementation: Add `chat_sessions` and `chat_messages` tables. Left sidebar in ChatPage shows recent sessions. Session restore populates messages array.
- Effort: 2-3 days
- Impact: Power users who use Chat for multi-session research tasks gain significant value

**P3-B: Inline Preview Editing (기안문)**
- Where: GianmunPage preview pane
- Fix: Add an "편집 모드" toggle on the preview panel header. When active, the preview becomes a `contenteditable` div. Changes update the `preview` state. Save button saves the edited content, not the original AI output.
- Effort: 1 day
- Impact: Eliminates the "copy AI output to 한글, edit there, paste back" workaround that many users will do

**P3-C: Attendees Tag Input (회의록)**
- Where: MeetingPage attendees field
- Fix: Build a simple tag input component using existing CSS variables. On comma or Enter keypress, convert the typed text into a removable chip. Output is joined as comma-separated string on form submit.
- Effort: half day
- Impact: Prevents invalid input; better represents the attendees data model

**P3-D: Regulation Search — AI-Assisted Explanation**
- Where: RegulationPage
- Fix: Add an "AI 조문 해석" button on each regulation result row that opens a Chat session pre-filled with the regulation text and the prompt: "다음 조문을 일반 공무원이 이해하기 쉽게 설명해주세요."
- Effort: half day
- Impact: Connects a currently isolated tool (법령 검색) to the AI assistant; high value for non-legal staff

**P3-E: PII Compliance Report Export**
- Where: PiiPage
- Fix: Backend generates a HWPX summary document: header with date/officer/department, table of findings per file (type, count, redacted value samples), footer with scan timestamp.
- Effort: 1 day (backend HWPX template + API endpoint + UI button)
- Impact: Converts PII scanning from an informal check into auditable compliance documentation

**P3-F: Document Search — Highlight in Preview**
- Where: SearchPage
- Fix: After selecting a search result, pass the query terms to HwpxPreview and highlight matching text spans using a mark element. Backend already returns the snippet; extend to include highlighted offsets.
- Effort: 1 day
- Impact: Dramatically improves search usability — users see exactly why a document matched

**P3-G: SetupWizard — In-App Model Download**
- Where: SetupWizard, models step
- Fix: Add a "다운로드" button next to each missing model. The button calls `POST /api/models/pull { model_id }` which streams progress via SSE. Progress bar per model in the wizard step.
- Effort: 1-2 days (backend SSE pull endpoint + frontend)
- Impact: Eliminates the terminal barrier for non-technical users; dramatically improves first-run success rate

**P3-H: Dark Mode**
- Already in backlog
- Implementation: CSS variables already abstracted perfectly for this. Add `[data-theme="dark"]` overrides for all color tokens. Toggle button in Topbar. Persist preference in localStorage.
- Effort: 1-2 days
- Impact: Reduces eye strain during long working sessions

---

## Part 6: Acceptance Criteria per Feature

### AC-01: 기안문 작성 (완전 재작성 기준)

| # | Criteria | Priority |
|---|----------|----------|
| 1 | Template selector renders as visual cards with icon, name, and one-line description | P2 |
| 2 | Subject field receives focus automatically when the page loads | P1 |
| 3 | Body instruction textarea displays a character counter (n/500) that turns amber at 400 and red at 500 | P2 |
| 4 | Clicking "AI 생성" shows a skeleton loading state in the preview panel before the first token arrives | P2 |
| 5 | Guard chips (date/PII/budget) animate in after streaming completes with a brief fade-in | P2 |
| 6 | A color legend for guard annotation types is shown below the guard chip bar | P2 |
| 7 | The preview panel offers an "편집 모드" toggle that enables inline editing of the generated text | P3 |
| 8 | "HWPX 저장" button shows the full target file path in a tooltip on hover | P1 |
| 9 | After successful save, a "파일 위치 열기" button appears in the success toast | P2 |
| 10 | Guard validation chip for PII shows a count: e.g., "PII 3건 발견" | P1 |

### AC-02: 회의록 작성

| # | Criteria | Priority |
|---|----------|----------|
| 1 | On first STT recording attempt, if the Whisper model is not downloaded, show a download progress modal before starting | P1 |
| 2 | During recording, a waveform animation (canvas) provides visual audio feedback | P3 |
| 3 | The red timer is displayed in MM:SS format with a pulsing red dot to the left | P1 |
| 4 | Transcribed text appends to existing content with a visual separator line between sessions | P2 |
| 5 | The attendees field accepts comma or Enter to create removable chips | P3 |
| 6 | AI generation streams token-by-token into the right panel (matches gianmun pattern) | P2 |
| 7 | The generated output auto-scrolls into view after streaming begins | P2 |
| 8 | The saved file name follows the format `회의록_[제목]_[YYYYMMDD].hwpx` | P2 |

### AC-03: 민원 답변

| # | Criteria | Priority |
|---|----------|----------|
| 1 | A single primary CTA "AI 분석 및 답변 초안 작성" triggers both classification and draft generation | P2 |
| 2 | The classification result (category, urgency, department) appears above the draft in a compact chip row | P2 |
| 3 | The draft response is displayed in an editable area — user can modify before saving | P2 |
| 4 | A "복사하기" button copies the full draft text to the clipboard | P2 |
| 5 | The user's `department_name` and `officer_name` from Settings are automatically appended to the closing of the draft | P2 |
| 6 | Character count is shown below the complaint input textarea | P2 |

### AC-04: AI 채팅

| # | Criteria | Priority |
|---|----------|----------|
| 1 | Config options (reasoning level, deep mode, model) are collapsed into a gear icon by default | P3 |
| 2 | Reasoning level labels are "빠른 답변 / 균형 / 깊은 분석" with tooltip explanations | P2 |
| 3 | Deep mode shows a tooltip: "AI가 답변 전 구체적인 질문을 합니다" | P2 |
| 4 | Character count is shown below the input textarea | P2 |
| 5 | Each AI message has a copy-to-clipboard button (visible on hover) | P2 |
| 6 | 대화 초기화 uses a styled modal, not window.confirm() | P1 |
| 7 | Chat sessions are persisted to SQLite and can be resumed from a session list | P3 |

### AC-05: PII 관리

| # | Criteria | Priority |
|---|----------|----------|
| 1 | Findings list shows: type chip + partially-masked matched value + 10-word context snippet | P2 |
| 2 | Clicking a finding row scrolls the heatmap to the finding position AND highlights it | P1 |
| 3 | Batch scan result presents a per-file table, not just aggregate totals | P2 |
| 4 | An "내보내기" button generates a HWPX compliance report | P3 |
| 5 | After masking, the toast shows the new file's full path | P1 |
| 6 | A loading skeleton is shown in the heatmap panel while scanning | P2 |

### AC-06: 대시보드

| # | Criteria | Priority |
|---|----------|----------|
| 1 | System status shown in a compact top bar, not as 3 prominent cards | P2 |
| 2 | Three primary action cards for 기안문/회의록/민원 are the visual centerpiece | P2 |
| 3 | Recent activity list shows the last 10 documents with modification date and file name | P2 |
| 4 | Each recent document shows PII status: 안전 / 미검사 / 발견 badge | P3 |
| 5 | When Ollama is offline, the status bar shows "Ollama 오프라인" in red with a "재연결 시도" button | P1 |
| 6 | Quick-entry AI chat field navigates to ChatPage with pre-filled content | P3 |

### AC-07: 설정

| # | Criteria | Priority |
|---|----------|----------|
| 1 | working_dir setting uses FolderPicker instead of a text input | P2 |
| 2 | Models tab shows which model is assigned to which task (기안문/회의록/민원/채팅) | P2 |
| 3 | A "STT 모델 다운로드" button with progress bar is present in the Models tab | P1 |
| 4 | Pipeline names in the Optimization tab show human-readable labels: "기안문 최적화 / 민원 최적화 / 회의록 최적화" | P2 |

### AC-08: 셋업 위저드

| # | Criteria | Priority |
|---|----------|----------|
| 1 | Step indicator shows text labels: "AI 엔진 > 모델 > 내 정보 > 완료" alongside the dots | P2 |
| 2 | "다음" button is disabled with a tooltip if the current step has a required action (e.g., Ollama not connected) | P2 |
| 3 | Each missing model in step 3 has a "다운로드" button that shows inline progress | P3 |
| 4 | STT model download option is offered in step 3 with a size warning and "나중에 설치" option | P2 |
| 5 | The final "시작하기" button uses a teal success style with a brief animation | P2 |

---

## Part 7: Implementation Priority Matrix

### Impact vs. Effort Assessment

```
HIGH IMPACT
    |
    |  P1-A (STT UX)          P2-E (Dashboard)    P3-A (Chat History)
    |  P2-D (Nav Groups)      P2-G (Complaint)    P3-G (Model Download)
    |  P1-B (Modals)          P2-C (Type Cards)
    |  P2-H (Findings)
    |
    |  P1-C (CSS vars)        P2-A/B (Counters)   P3-B (Inline Edit)
    |  P1-D (Contrast)        P2-F (FolderPicker) P3-D (Reg AI)
    |
LOW IMPACT
    +----|---------------|---------------|---
      LOW EFFORT      MED EFFORT    HIGH EFFORT
```

### Quick Wins (< 4 hours each)
1. **P1-C** — Define missing CSS variables (15 min)
2. **P1-D** — Darken ink3 token (30 min)
3. **P2-A** — Character counter on GianmunPage body_instruction (1 hour)
4. **P2-B** — Character counter on ChatPage textarea (1 hour)
5. **P2-F** — Settings working_dir FolderPicker (1 hour)
6. **P2-D** — Navigation grouping with separators (2 hours)

### Core Improvements (1–5 days each)
1. **P1-B** — ConfirmModal component, replace all window.confirm() (4 hours)
2. **P1-A** — STT model download progress UI (2 days: API endpoint + UI)
3. **P2-H** — PII findings human-readable context (4 hours)
4. **P2-G** — Complaint unified action (3 hours)
5. **P2-C** — Gianmun document type visual card selector (1 day)
6. **P2-E (Phase 1)** — Dashboard system bar + 3 action cards (2 days)
7. **P2-E (Phase 2)** — Dashboard recent activity list (1 day)

### Strategic Enhancements (1–2 weeks each)
1. **P3-A** — Chat session persistence (3 days)
2. **P3-E** — PII compliance report export (2 days)
3. **P3-G** — In-wizard model download (2 days)
4. **P3-B** — Inline preview editing for gianmun (1 day)
5. **P3-H** — Dark mode (2 days)

---

## Part 8: UX Success Metrics

### Quantitative (measurable via usage logs)

| Metric | Current Baseline | Target (6 months) |
|--------|-----------------|-------------------|
| 기안문 time-to-save (first generation) | ~25-40 min | < 10 min |
| Setup wizard completion rate (first-run) | Unknown (STT download blocks many) | > 90% |
| PII scan usage per document created | Low (requires navigation to separate page) | > 80% of exported docs |
| Complaint draft generation button clicks per session | 2 (classify + draft) | 1 (combined action) |
| Chat session abandonment (navigate away mid-stream) | Unknown | < 10% |
| Error toast occurrences of "저장 실패" without resolution path | Frequent | 0 (all errors have actionable copy) |

### Qualitative (observable in user testing)

1. **First-run success:** A non-technical civil servant can install the app and produce their first 기안문 without consulting IT support
2. **PII confidence:** Users feel certain — not just hopeful — that their documents are clean before submission
3. **AI trust:** Users understand that all processing is local; they can explain the privacy guarantee to a colleague
4. **Tool invisibility:** Users describe the app as "the thing that helps me write documents" — not "the AI app" — meaning the technology is subordinate to the work

### Emotional Arc (per session)

```
Open app        →  Dashboard     →  Feature page  →  AI generates  →  Save         →  Close
Familiar,          Oriented,        Focused,          Impressed,        Relieved,       Confident
grounded           purposeful       no distraction    trusting          in control
```

The goal is that the user never experiences confusion, anxiety, or uncertainty at any step in this arc. Every loading state tells them what is happening. Every error tells them what to do next. Every success state confirms that their work is saved and safe.

---

## Part 9: Visual Design Direction Notes

The existing visual design is solid and does not need a major overhaul. These are targeted refinements:

### Typography
- Current: `h1=1.6rem / h2=1.3rem / h3=1.1rem / body=1rem / small=0.85rem / micro=0.78rem`
- Issue: `h1` is never used inside the app (only SetupWizard) — the de-facto page title is `h2`. Visually, `1.3rem` with `font-weight:700` is acceptable but a bit compact.
- Recommendation: Increase the page title (currently rendered as `<h2>`) to `1.4rem` and add a `color: var(--navy)` override so it feels more authoritative. Add a subtle bottom-border or spacing separator between the page title and the first content element.

### Spacing
- Content padding is 24px — appropriate for desktop, but on a typical 1920×1080 government PC with a 1920px viewport, the max-width of 1400px combined with the 220px sidebar means content is 24px from the sidebar edge. This should have `margin: 0 auto` within the content area to center it when viewport is wide.
- Cards use 18px padding — consistent and good. Do not change.
- Form groups use 14px bottom margin — acceptable for dense forms; consider increasing to 18px for forms that need breathing room (Settings profile tab).

### Microinteractions to Add
1. **Navigation active indicator:** The current `border-right: 3px solid var(--teal2)` is fine. Add a very subtle `background` transition on hover: `transition: background 0.2s ease` (already present at 0.15s — could extend slightly).
2. **Card hover on Dashboard action cards:** `transform: translateY(-2px)` with `box-shadow` increase. Standard depth affordance.
3. **Guard chips animate-in:** Use `@keyframes chipIn { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }` applied with a stagger delay per chip (0ms, 80ms, 160ms).
4. **Thinking panel expand/collapse:** The current `overflow: hidden` toggle works but has no animation. Add `max-height` CSS transition for a smooth reveal.
5. **STT recording pulse:** The current red dot is static text. Replace with a CSS pulse animation that conveys live audio capture.

### Empty States
All empty states currently use a large emoji + a single instruction line. Improve by adding a contextual action:
- GianmunPage right panel empty: `✍️ AI 생성 버튼을 클릭하면 기안문 초안이 표시됩니다` + [AI 생성 버튼으로 이동] anchor that scrolls to the left panel
- MeetingPage right panel empty: `📋 회의 내용을 입력한 후 생성 버튼을 클릭하세요` — add estimated time: "(AI 처리 약 15-30초)"
- ChatPage empty state: keep the example prompts (well-designed) — add a `font-size: 1.1rem` on `.empty-title` for more presence

### Focus States (Keyboard Navigation)
All interactive elements need visible focus rings. The current design correctly uses `focus-visible` (not `focus`) to avoid showing rings on mouse click. Verify:
- All `<button>` elements: `focus-visible { outline: 2px solid var(--teal); outline-offset: 2px; }`
- All `<a>` and `<NavLink>` elements: same outline
- Sidebar nav links: the current `a.active` style may obscure the focus ring — ensure the ring is visible on top of the active background

---

*Document prepared by: UX Polish Designer Agent — GM-AI-Hub project*
*Based on full source code audit of frontend/src and backend/ directories*
*Last updated: 2026-02-24*
