import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { fetchJSON, API } from '../utils/api'
import { timeAgo } from '../utils/date'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [aiStatus, setAiStatus] = useState(null)
  const [models, setModels] = useState([])
  const [optStatus, setOptStatus] = useState(null)

  useEffect(() => {
    fetchJSON(API.health).then(setStats).catch(() => {})
    fetchJSON(API.healthOllama).then(setAiStatus).catch(() => setAiStatus({ status: 'offline' }))
    fetchJSON(API.models).then(d => { if (d?.models) setModels(d.models.filter(m => m.available)) }).catch(() => {})
    fetchJSON(API.optimizeStatus).then(setOptStatus).catch(() => {})
  }, [])

  return (
    <div className="page-dashboard">
      <h2>대시보드</h2>

      <div className="dashboard-grid">
        {/* 시스템 상태 */}
        <div className="card">
          <div className="card-header">시스템 상태</div>
          <div className="card-body">
            <div className="stat-row">
              <span>서버</span>
              <span className={`badge ${stats ? 'badge-success' : 'badge-error'}`}>
                {stats ? '정상' : '확인 중...'}
              </span>
            </div>
            {stats?.version && (
              <div className="stat-row">
                <span>버전</span>
                <span>{stats.version}</span>
              </div>
            )}
            {stats?.document_count !== undefined && (
              <div className="stat-row">
                <span>문서 수</span>
                <span className="stat-value">{stats.document_count}</span>
              </div>
            )}
          </div>
        </div>

        {/* AI 엔진 */}
        <div className="card">
          <div className="card-header">AI 엔진 (Ollama)</div>
          <div className="card-body">
            <div className="stat-row">
              <span>상태</span>
              <span className={`badge ${aiStatus?.status === 'ok' ? 'badge-success' : 'badge-error'}`}>
                {aiStatus?.status === 'ok' ? '연결됨' : '오프라인'}
              </span>
            </div>
            {models.length > 0 && (
              <div className="stat-row">
                <span>사용 가능 모델</span>
                <span className="stat-value">{models.length}개</span>
              </div>
            )}
            {models.slice(0, 3).map(m => (
              <div key={m.id} className="stat-row" style={{ fontSize: '0.85rem' }}>
                <span>{m.name}</span>
                <span style={{ color: 'var(--ink3)' }}>{m.param_size}B</span>
              </div>
            ))}
          </div>
        </div>

        {/* MIPROv2 최적화 */}
        <div className="card">
          <div className="card-header">프롬프트 최적화</div>
          <div className="card-body">
            {optStatus ? (
              <>
                <div className="stat-row">
                  <span>상태</span>
                  <span className={`badge ${optStatus.optimized ? 'badge-success' : 'badge-warning'}`}>
                    {optStatus.optimized ? '최적화됨' : '미최적화'}
                  </span>
                </div>
                {optStatus.last_optimized && (
                  <div className="stat-row">
                    <span>마지막 최적화</span>
                    <span>{timeAgo(optStatus.last_optimized)}</span>
                  </div>
                )}
                {optStatus.version && (
                  <div className="stat-row">
                    <span>버전</span>
                    <span>v{optStatus.version}</span>
                  </div>
                )}
              </>
            ) : (
              <p style={{ color: 'var(--ink3)' }}>로딩 중...</p>
            )}
          </div>
        </div>

        {/* 빠른 링크 */}
        <div className="card">
          <div className="card-header">빠른 작업</div>
          <div className="card-body quick-links">
            <Link to="/gianmun" className="btn btn-primary">기안문 작성</Link>
            <Link to="/search" className="btn btn-secondary">문서 검색</Link>
            <Link to="/chat" className="btn btn-secondary">AI 채팅</Link>
            <Link to="/pii" className="btn btn-secondary">PII 검사</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
