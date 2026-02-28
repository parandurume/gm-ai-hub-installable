import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { fetchJSON, API } from '../utils/api'
import { timeAgo } from '../utils/date'

const PRIMARY_ACTIONS = [
  { to: '/draft',     icon: '✍️',  title: '기안문 작성',  desc: '공문서 AI 초안 생성 + HWPX 저장' },
  { to: '/chat',      icon: '🤖', title: 'AI 채팅',      desc: '공문서 작성 전반 어시스턴트' },
  { to: '/complaint', icon: '📨', title: '민원 답변',     desc: '민원 분류 + 답변 초안 자동 생성' },
]

const SECONDARY_ACTIONS = [
  { to: '/meeting',    icon: '📋', label: '회의록' },
  { to: '/search',     icon: '🔍', label: '문서 검색' },
  { to: '/regulation', icon: '⚖️',  label: '법령 검색' },
  { to: '/pii',        icon: '🔒', label: 'PII 검사' },
  { to: '/diff',       icon: '🔄', label: '문서 비교' },
  { to: '/files',      icon: '📂', label: '문서 관리' },
]

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [aiStatus, setAiStatus] = useState(null)
  const [models, setModels] = useState([])
  const [optStatus, setOptStatus] = useState(null)
  const [recentDocs, setRecentDocs] = useState([])

  useEffect(() => {
    fetchJSON(API.health).then(setStats).catch(() => {})
    fetchJSON(API.healthOllama).then(setAiStatus).catch(() => setAiStatus({ status: 'offline' }))
    fetchJSON(API.models).then(d => { if (d?.models) setModels(d.models.filter(m => m.available)) }).catch(() => {})
    fetchJSON(API.optimizeStatus).then(setOptStatus).catch(() => {})
    fetchJSON(API.documents).then(d => setRecentDocs((d?.files || []).slice(0, 8))).catch(() => {})
  }, [])

  const serverOk = !!stats
  const aiOk = aiStatus?.status === 'ok'

  return (
    <div className="page-dashboard">
      <h2>대시보드</h2>

      {/* Compact system status bar */}
      <div className="status-bar">
        <div className="status-bar-item">
          <span className={`status-dot-sm ${serverOk ? 'ok' : 'err'}`} />
          <span>서버 {serverOk ? '정상' : '확인 중'}</span>
          {stats?.version && <span className="status-meta">v{stats.version}</span>}
        </div>
        <div className="status-bar-sep" />
        <div className="status-bar-item">
          <span className={`status-dot-sm ${aiOk ? 'ok' : 'err'}`} />
          <span>Ollama {aiOk ? '연결됨' : '오프라인'}</span>
          {models.length > 0 && <span className="status-meta">{models.length}개 모델</span>}
        </div>
        <div className="status-bar-sep" />
        <div className="status-bar-item">
          <span className={`status-dot-sm ${optStatus?.optimized ? 'ok' : 'warn'}`} />
          <span>프롬프트 {optStatus?.optimized ? '최적화됨' : '미최적화'}</span>
          {optStatus?.last_optimized && (
            <span className="status-meta">{timeAgo(optStatus.last_optimized)}</span>
          )}
        </div>
        {stats?.document_count !== undefined && (
          <>
            <div className="status-bar-sep" />
            <div className="status-bar-item">
              <span>문서 {stats.document_count}개</span>
            </div>
          </>
        )}
      </div>

      {/* Recent documents */}
      {recentDocs.length > 0 && (
        <div className="recent-docs">
          <div className="recent-docs-header">최근 문서</div>
          <div className="recent-docs-list">
            {recentDocs.map(f => (
              <Link key={f.path} to="/files" className="recent-doc-item">
                <span className="recent-doc-name">{f.filename}</span>
                <span className="badge badge-gray">{f.ext}</span>
                <span className="recent-doc-time">{timeAgo(f.modified_at * 1000)}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Primary action cards */}
      <div className="dashboard-primary-grid">
        {PRIMARY_ACTIONS.map(a => (
          <Link key={a.to} to={a.to} className="dashboard-action-card">
            <span className="dac-icon">{a.icon}</span>
            <div className="dac-body">
              <div className="dac-title">{a.title}</div>
              <div className="dac-desc">{a.desc}</div>
            </div>
            <span className="dac-arrow">›</span>
          </Link>
        ))}
      </div>

      {/* Secondary quick links */}
      <div className="dashboard-secondary-grid">
        {SECONDARY_ACTIONS.map(a => (
          <Link key={a.to} to={a.to} className="dashboard-quick-link">
            <span>{a.icon}</span>
            <span>{a.label}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
