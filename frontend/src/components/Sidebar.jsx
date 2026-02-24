import { memo } from 'react'
import { NavLink } from 'react-router-dom'

const NAV_GROUPS = [
  {
    label: '문서 작성',
    items: [
      { to: '/gianmun',   icon: '✍️',  label: '기안문 작성' },
      { to: '/meeting',   icon: '📋', label: '회의록' },
      { to: '/complaint', icon: '📨', label: '민원 답변' },
    ],
  },
  {
    label: '검색 / 분석',
    items: [
      { to: '/search',     icon: '🔍', label: '문서 검색' },
      { to: '/regulation', icon: '⚖️',  label: '법령 검색' },
      { to: '/pii',        icon: '🔒', label: 'PII 관리' },
      { to: '/diff',       icon: '🔄', label: '문서 비교' },
    ],
  },
  {
    label: '보조 도구',
    items: [
      { to: '/chat',  icon: '🤖', label: 'AI 채팅' },
      { to: '/files', icon: '📂', label: '문서 관리' },
    ],
  },
]

/* rerender-memo: Sidebar is static; memo avoids re-renders from parent. */
export default memo(function Sidebar({ open, onClose }) {
  return (
    <nav className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="sidebar-logo">
        <h1>GM-AI-Hub</h1>
        <span>광명시 AI 공문서 시스템</span>
      </div>

      {/* Dashboard always first, ungrouped */}
      <NavLink to="/" end className="sidebar-home-link" onClick={onClose}>
        <span className="nav-icon">🏠</span>
        대시보드
      </NavLink>

      <div className="sidebar-nav">
        {NAV_GROUPS.map(group => (
          <div key={group.label} className="nav-group">
            <div className="nav-group-label">{group.label}</div>
            {group.items.map(item => (
              <NavLink key={item.to} to={item.to} onClick={onClose}>
                <span className="nav-icon">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      <NavLink to="/settings" className="sidebar-settings-link" onClick={onClose}>
        <span className="nav-icon">⚙️</span>
        설정
      </NavLink>

      <div className="sidebar-footer">v3.0.0</div>
    </nav>
  )
})
