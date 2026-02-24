import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { fetchJSON, API } from '../utils/api'

const PAGE_TITLES = {
  '/':           '\uB300\uC2DC\uBCF4\uB4DC',
  '/files':      '\uBB38\uC11C \uAD00\uB9AC',
  '/gianmun':    '\uAE30\uC548\uBB38 \uC791\uC131',
  '/search':     '\uBB38\uC11C \uAC80\uC0C9',
  '/chat':       'AI \uCC44\uD305',
  '/meeting':    '\uD68C\uC758\uB85D',
  '/complaint':  '\uBBFC\uC6D0 \uB2F5\uBCC0',
  '/regulation': '\uBC95\uB839 \uAC80\uC0C9',
  '/pii':        'PII \uAD00\uB9AC',
  '/diff':       '\uBB38\uC11C \uBE44\uAD50',
  '/settings':   '\uC124\uC815',
}

export default function Topbar({ onToggleSidebar }) {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] || ''
  const [ollamaOk, setOllamaOk] = useState(null)

  useEffect(() => {
    const check = () => {
      fetchJSON(API.healthOllama)
        .then(d => setOllamaOk(d?.status === 'ok'))
        .catch(() => setOllamaOk(false))
    }
    check()
    const interval = setInterval(check, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button className="hamburger-btn" onClick={onToggleSidebar} aria-label="메뉴 열기">
          &#9776;
        </button>
        <span className="topbar-title">{title}</span>
      </div>
      <div className="topbar-actions">
        <span className={`ollama-status ${ollamaOk === true ? 'online' : ollamaOk === false ? 'offline' : ''}`}>
          <span className="ollama-dot" />
          {ollamaOk === null ? 'Ollama 확인 중' : ollamaOk ? 'Ollama 연결됨' : 'Ollama 오프라인'}
        </span>
      </div>
    </header>
  )
}
