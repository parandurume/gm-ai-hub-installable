import { useState } from 'react'

export default function ThinkingPanel({ content, streaming = false }) {
  const [open, setOpen] = useState(streaming)

  if (!content) return null

  return (
    <div className={`thinking-panel${streaming ? ' thinking-streaming' : ''}`}>
      <button
        type="button"
        className="thinking-toggle"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span>{open ? '\u25BC' : '\u25B6'}</span>
        <span>{open ? 'AI 추론 과정 접기' : 'AI 추론 과정 펼치기'}</span>
        {streaming && <span className="thinking-pulse" />}
      </button>
      {open && <div className="thinking-content">{content}</div>}
    </div>
  )
}
