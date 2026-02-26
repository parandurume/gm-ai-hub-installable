# UI/UX Agent Memory — GM-AI-Hub

## Project Stack
- Framework: React + Vite (frontend), FastAPI (backend)
- Styling: Plain CSS with custom design tokens (no CSS framework)
- Routing: React Router v6
- Streaming: WebSocket (chat), SSE (gianmun body generation, optimization)
- State: Local useState per page (no global store like Zustand/Redux)

## Design System Tokens (global.css)
- Colors: --navy (#0F2040), --teal (#007A5E), --teal2 (#00A87A), --amber (#D4860A), --red (#C0392B)
- Backgrounds: --paper (#F7F5F0), --paper2 (#EDEAE3)
- Text: --ink (#1C1C22), --ink2 (#44444F), --ink3 (#6B6B7D)
- Border: --border (#D8D5CC)
- Layout: --sidebar-width (220px), --topbar-height (54px)
- Base font-size: 14px (html root)
- Font: Noto Sans KR (body), Noto Serif KR (serif), JetBrains Mono (code)

## Key Pages
- /chat — ChatPage.jsx (WebSocket streaming, model selector, reasoning level, deep mode, HWPX save)
- /gianmun — GianmunPage.jsx (SSE streaming, split-view, guard validation, folder picker)
- /pii — PiiPage.jsx (3-panel layout: file list | heatmap preview | findings)
- /settings — SettingsPage.jsx (4 tabs: general, models, optimization, samples)
- / — Dashboard.jsx (status cards + quick links)

## Key Patterns Established
- Toast notifications: top-right, 4000ms auto-dismiss, no manual close button
- Error feedback: only via toast (no inline form errors)
- Loading state: button text changes to "...중" or spinner component
- Empty states: preview-empty class with large emoji + text
- Navigation: fixed left sidebar (220px) + sticky topbar (54px)
- Chat bubbles: user=right/teal, assistant=left/white+border
- Streaming: cursor-blink animation during text stream, status-dot pulse while waiting

## Confirmed UX Gaps (from audit 2026-02-23)
- See ui-ux-audit-2026-02-23.md for full ranked recommendations
- Top issues: no mobile layout, no focus management on new messages, toast has no close button,
  ModelSelector cards are not keyboard accessible (div+onClick not button), chat text not
  markdown-rendered, no confirmation before 대화 초기화, HWPX save during streaming not guarded,
  no character count on chat textarea, pii-tri-view breaks below ~1000px, settings tabs not URL-linked
