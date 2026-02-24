import { memo } from 'react'
import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/',           icon: '\uD83C\uDFE0', label: '\uB300\uC2DC\uBCF4\uB4DC' },
  { to: '/files',      icon: '\uD83D\uDCC2', label: '\uBB38\uC11C \uAD00\uB9AC' },
  { to: '/gianmun',    icon: '\u270D\uFE0F',  label: '\uAE30\uC548\uBB38 \uC791\uC131' },
  { to: '/search',     icon: '\uD83D\uDD0D', label: '\uBB38\uC11C \uAC80\uC0C9' },
  { to: '/chat',       icon: '\uD83E\uDD16', label: 'AI \uCC44\uD305' },
  { to: '/meeting',    icon: '\uD83D\uDCCB', label: '\uD68C\uC758\uB85D' },
  { to: '/complaint',  icon: '\uD83D\uDCE8', label: '\uBBFC\uC6D0 \uB2F5\uBCC0' },
  { to: '/regulation', icon: '\u2696\uFE0F',  label: '\uBC95\uB839 \uAC80\uC0C9' },
  { to: '/pii',        icon: '\uD83D\uDD12', label: 'PII \uAD00\uB9AC' },
  { to: '/diff',       icon: '\uD83D\uDD04', label: '\uBB38\uC11C \uBE44\uAD50' },
  { to: '/settings',   icon: '\u2699\uFE0F',  label: '\uC124\uC815' },
]

/* rerender-memo: Sidebar is static; memo avoids re-renders from parent. */
export default memo(function Sidebar({ open, onClose }) {
  return (
    <nav className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="sidebar-logo">
        <h1>GM-AI-Hub</h1>
        <span>광명시 AI 공문서 시스템</span>
      </div>
      <div className="sidebar-nav">
        {NAV_ITEMS.map(item => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'} onClick={onClose}>
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </div>
      <div className="sidebar-footer">v2.0.0</div>
    </nav>
  )
})
