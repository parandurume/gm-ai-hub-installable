import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchJSON, API } from '../utils/api'
import ModelSelector from '../components/ModelSelector'
import SampleManager from '../components/SampleManager'
import { useToast } from '../hooks/useToast'

export default function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'general'
  const setTab = (t) => setSearchParams({ tab: t })
  const [settings, setSettings] = useState({})
  const [models, setModels] = useState([])
  const [optStatus, setOptStatus] = useState(null)
  const [optProgress, setOptProgress] = useState(null)
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  useEffect(() => {
    fetchJSON(API.settings).then(setSettings).catch(() => {})
    fetchJSON(API.models).then(d => setModels(d?.models || [])).catch(() => {})
    fetchJSON(API.optimizeStatus).then(setOptStatus).catch(() => {})
  }, [])

  async function handleSaveSettings() {
    setLoading(true)
    try {
      await fetch(API.settings, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      toast('설정 저장 완료', 'success')
    } catch {
      toast('설정 저장 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function handleOptimize(pipeline) {
    toast('최적화를 시작합니다...', 'info')
    try {
      const evtSource = new EventSource(`${API.optimizeRun}?pipeline=${pipeline}`)
      evtSource.onmessage = (e) => {
        const data = JSON.parse(e.data)
        if (data.type === 'progress') setOptProgress(data)
        else if (data.type === 'done') {
          setOptProgress(null)
          toast('최적화 완료', 'success')
          evtSource.close()
          fetchJSON(API.optimizeStatus).then(setOptStatus).catch(() => {})
        } else if (data.type === 'error') {
          toast(`최적화 실패: ${data.message}`, 'error')
          evtSource.close()
        }
      }
      evtSource.onerror = () => {
        evtSource.close()
        setOptProgress(null)
      }
    } catch {
      toast('최적화 시작 실패', 'error')
    }
  }

  async function handleReloadPipelines() {
    try {
      await fetch(API.optimizeReload, { method: 'POST' })
      toast('파이프라인 리로드 완료', 'success')
    } catch {
      toast('리로드 실패', 'error')
    }
  }

  function updateSetting(key, value) {
    setSettings(s => ({ ...s, [key]: value }))
  }

  const TABS = [
    { id: 'general', label: '일반' },
    { id: 'models', label: '모델 관리' },
    { id: 'optimization', label: '프롬프트 최적화' },
    { id: 'samples', label: '학습 샘플' },
  ]

  return (
    <div className="page-settings">
      <h2>설정</h2>

      <div className="tab-bar">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >{t.label}</button>
        ))}
      </div>

      {tab === 'general' && (
        <div className="settings-section">
          <div className="form-group">
            <label>작업 폴더</label>
            <input
              type="text"
              value={settings.working_dir || ''}
              onChange={e => updateSetting('working_dir', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Ollama URL</label>
            <input
              type="text"
              value={settings.ollama_url || 'http://127.0.0.1:11434'}
              onChange={e => updateSetting('ollama_url', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>PII 내보내기 검사</label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={settings.pii_scan_on_export !== false}
                onChange={e => updateSetting('pii_scan_on_export', e.target.checked)}
              />
              내보내기 시 PII 자동 검사
            </label>
          </div>
          <button className="btn btn-primary" onClick={handleSaveSettings} disabled={loading}>
            {loading ? '저장 중...' : '설정 저장'}
          </button>
        </div>
      )}

      {tab === 'models' && (
        <div className="settings-section">
          <h3>사용 가능한 모델</h3>
          <table className="table">
            <thead>
              <tr><th>모델</th><th>크기</th><th>RAM</th><th>상태</th><th>기능</th></tr>
            </thead>
            <tbody>
              {models.map(m => (
                <tr key={m.id}>
                  <td>{m.name}</td>
                  <td>{m.param_size}B</td>
                  <td>{m.ram_gb}GB</td>
                  <td>
                    <span className={`badge ${m.available ? 'badge-success' : 'badge-error'}`}>
                      {m.available ? '사용 가능' : '미설치'}
                    </span>
                  </td>
                  <td>
                    {m.supports_thinking && <span className="badge badge-info" style={{ marginRight: 4 }}>Thinking</span>}
                    {m.supports_embedding && <span className="badge badge-info">Embedding</span>}
                  </td>
                </tr>
              ))}
              {models.length === 0 && (
                <tr><td colSpan={5} style={{ textAlign: 'center', padding: 40, color: 'var(--ink3)' }}>모델 정보를 불러오는 중...</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'optimization' && (
        <div className="settings-section">
          <h3>MIPROv2 프롬프트 최적화</h3>

          {optStatus && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-body">
                <div className="stat-row">
                  <span>상태</span>
                  <span className={`badge ${optStatus.optimized ? 'badge-success' : 'badge-warning'}`}>
                    {optStatus.optimized ? '최적화됨' : '미최적화'}
                  </span>
                </div>
                {optStatus.last_optimized && (
                  <div className="stat-row">
                    <span>마지막 실행</span>
                    <span>{new Date(optStatus.last_optimized).toLocaleString('ko')}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {optProgress && (
            <div className="card" style={{ marginBottom: 20, borderColor: 'var(--teal)' }}>
              <div className="card-header">최적화 진행 중</div>
              <div className="card-body">
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${optProgress.percent || 0}%` }} />
                </div>
                <p style={{ marginTop: 8, fontSize: '0.85rem', color: 'var(--ink3)' }}>
                  {optProgress.message || '처리 중...'}
                </p>
              </div>
            </div>
          )}

          <div className="form-actions" style={{ flexWrap: 'wrap', gap: 8 }}>
            {['gianmun', 'docent', 'complaint', 'meeting'].map(p => (
              <button
                key={p}
                className="btn btn-primary"
                onClick={() => handleOptimize(p)}
                disabled={!!optProgress}
              >
                {p} 최적화
              </button>
            ))}
            <button className="btn btn-secondary" onClick={handleReloadPipelines}>
              파이프라인 리로드
            </button>
          </div>
        </div>
      )}

      {tab === 'samples' && (
        <div className="settings-section">
          <SampleManager />
        </div>
      )}
    </div>
  )
}
