import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { fetchJSON, API } from '../utils/api'
import ConfirmModal from './ConfirmModal'

const PAGE_TITLES = {
  '/':           '대시보드',
  '/files':      '문서 관리',
  '/gianmun':    '기안문 작성',
  '/search':     '문서 검색',
  '/chat':       'AI 채팅',
  '/meeting':    '회의록',
  '/complaint':  '민원 답변',
  '/regulation': '법령 검색',
  '/pii':        'PII 관리',
  '/diff':       '문서 비교',
  '/settings':   '설정',
}

function QuitDoneScreen() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', height: '100vh',
      fontFamily: 'sans-serif', color: '#444', gap: 16,
    }}>
      <div style={{ fontSize: '2rem' }}>&#x23FB;</div>
      <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>앱이 종료되었습니다</div>
      <div style={{ fontSize: '0.9rem', color: '#888' }}>
        이 탭을 직접 닫아주세요
      </div>
      <button
        onClick={() => window.close()}
        style={{
          marginTop: 8, padding: '8px 20px', border: '1px solid #ccc',
          borderRadius: 6, background: '#f5f5f5', cursor: 'pointer',
          fontSize: '0.9rem', color: '#333',
        }}
      >
        탭 닫기
      </button>
    </div>
  )
}

export default function Topbar({ onToggleSidebar }) {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] || ''
  const [ollamaOk, setOllamaOk] = useState(null)
  const [quitConfirm, setQuitConfirm] = useState(false)
  const [quitting, setQuitting] = useState(false)

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

  async function doQuit() {
    setQuitConfirm(false)
    setQuitting(true)
    try {
      await fetch(API.quit, { method: 'POST' })
    } catch {
      // Server terminates before response returns — this is expected
    }
    // Try to close the tab. Browsers block this if the page was opened
    // by the OS (webbrowser.open), not by window.open() in JS.
    // If it fails, QuitDoneScreen with a manual "탭 닫기" button is shown.
    window.close()
  }

  if (quitting) {
    return <QuitDoneScreen />
  }

  return (
    <>
      <ConfirmModal
        open={quitConfirm}
        title="앱 종료"
        message="서버와 트레이 아이콘이 모두 종료됩니다. 계속하시겠습니까?"
        confirmLabel="종료"
        danger
        onConfirm={doQuit}
        onCancel={() => setQuitConfirm(false)}
      />

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
          <button
            className="btn-quit"
            onClick={() => setQuitConfirm(true)}
            title="앱 종료"
            aria-label="앱 종료"
          >&#x23FB;</button>
        </div>
      </header>
    </>
  )
}
