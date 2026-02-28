import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchJSON, API } from '../utils/api'
import ModelSelector from '../components/ModelSelector'
import SampleManager from '../components/SampleManager'
import FolderPicker from '../components/FolderPicker'
import { useToast } from '../hooks/useToast'

const PIPELINES = [
  { id: 'draft',     label: '기안문 최적화' },
  { id: 'docent',    label: '도슨트 최적화' },
  { id: 'complaint', label: '민원 최적화' },
  { id: 'meeting',   label: '회의록 최적화' },
]

export default function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'general'
  const setTab = (t) => setSearchParams({ tab: t })
  const [settings, setSettings] = useState({})
  const [models, setModels] = useState([])
  const [optStatus, setOptStatus] = useState(null)
  const [optProgress, setOptProgress] = useState(null)
  const [loading, setLoading] = useState(false)
  const [dirPickerOpen, setDirPickerOpen] = useState(false)
  const [pullState, setPullState] = useState({}) // { [modelId]: { active, status, pct, error } }
  const pullEsRef = useRef({}) // { [modelId]: EventSource } — for cancel
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

  function handlePull(modelId) {
    setPullState(s => ({ ...s, [modelId]: { active: true, status: '연결 중...', pct: 0, error: null } }))
    const es = new EventSource(`${API.modelsPullStream}?model=${encodeURIComponent(modelId)}`)
    pullEsRef.current[modelId] = es
    es.onmessage = (e) => {
      if (e.data === '[DONE]') {
        es.close()
        delete pullEsRef.current[modelId]
        setPullState(s => ({ ...s, [modelId]: { active: false, status: '완료', pct: 100, error: null } }))
        fetchJSON(API.models).then(d => setModels(d?.models || [])).catch(() => {})
        toast(`${modelId} 설치 완료`, 'success')
        return
      }
      try {
        const d = JSON.parse(e.data)
        if (d.error) {
          es.close()
          delete pullEsRef.current[modelId]
          setPullState(s => ({ ...s, [modelId]: { active: false, status: '오류', pct: 0, error: d.error } }))
          toast(`다운로드 실패: ${d.error}`, 'error')
          return
        }
        const pct = d.total ? Math.round((d.completed || 0) / d.total * 100) : null
        setPullState(s => ({
          ...s,
          [modelId]: { active: true, status: d.status || '다운로드 중...', pct: pct ?? s[modelId]?.pct ?? 0, error: null },
        }))
      } catch {}
    }
    es.onerror = () => {
      es.close()
      delete pullEsRef.current[modelId]
      setPullState(s => ({ ...s, [modelId]: { active: false, status: '연결 오류', pct: 0, error: '연결이 끊어졌습니다' } }))
      toast('다운로드 연결 오류', 'error')
    }
  }

  function handleCancelPull(modelId) {
    const es = pullEsRef.current[modelId]
    if (es) { es.close(); delete pullEsRef.current[modelId] }
    setPullState(s => ({ ...s, [modelId]: { active: false, status: '', pct: 0, error: null } }))
    toast(`${modelId} 다운로드 취소됨`, 'info')
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
    { id: 'profile', label: '내 정보' },
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

      {tab === 'profile' && (
        <div className="settings-section">
          <p style={{ marginBottom: 20, color: 'var(--ink3)', fontSize: '0.9rem' }}>
            문서 작성 시 자동으로 입력되는 기본 정보입니다.
          </p>
          <div className="form-group">
            <label>부서명</label>
            <input
              type="text"
              value={settings.department_name || ''}
              onChange={e => updateSetting('department_name', e.target.value)}
              placeholder="예: 정보통신과"
            />
          </div>
          <div className="form-group">
            <label>담당자 이름</label>
            <input
              type="text"
              value={settings.officer_name || ''}
              onChange={e => updateSetting('officer_name', e.target.value)}
              placeholder="예: 홍길동"
            />
          </div>
          <button className="btn btn-primary" onClick={handleSaveSettings} disabled={loading}>
            {loading ? '저장 중...' : '저장'}
          </button>
        </div>
      )}

      {tab === 'general' && (
        <div className="settings-section">
          <div className="form-group">
            <label>작업 폴더</label>
            <div className="save-path-row">
              <div className={`save-path-display${settings.working_dir ? '' : ' empty'}`}>
                {settings.working_dir || '기본 경로 (문서 폴더)'}
              </div>
              {settings.working_dir && (
                <button className="save-path-clear" onClick={() => updateSetting('working_dir', '')} title="초기화">&times;</button>
              )}
              <button className="btn btn-browse" onClick={() => setDirPickerOpen(true)}>찾아보기</button>
            </div>
          </div>

          <FolderPicker
            open={dirPickerOpen}
            onClose={() => setDirPickerOpen(false)}
            onSelect={path => { updateSetting('working_dir', path); setDirPickerOpen(false) }}
            mode="folder"
          />
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
          <div className="form-group">
            <label>STT 음성 인식 모델</label>
            <select className="select"
              value={settings.stt_model || 'medium'}
              onChange={e => updateSetting('stt_model', e.target.value)}>
              <option value="tiny">tiny (~40 MB, 빠름)</option>
              <option value="base">base (~140 MB)</option>
              <option value="small">small (~480 MB)</option>
              <option value="medium">medium (~1.5 GB, 권장)</option>
              <option value="large-v3">large-v3 (~3 GB, 최고 정확도)</option>
            </select>
          </div>
          <div className="form-group">
            <label>STT 언어</label>
            <select className="select"
              value={settings.stt_language || 'ko'}
              onChange={e => updateSetting('stt_language', e.target.value)}>
              <option value="ko">한국어</option>
              <option value="en">English</option>
              <option value="ja">日本語</option>
              <option value="zh">中文</option>
              <option value="auto">자동 감지</option>
            </select>
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
              <tr><th>모델</th><th>크기</th><th>RAM</th><th>상태</th><th>기능</th><th>액션</th></tr>
            </thead>
            <tbody>
              {models.map(m => {
                const ps = pullState[m.id]
                return (
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
                    <td style={{ minWidth: 160 }}>
                      {!m.available && !ps?.active && !ps?.pct && (
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '3px 10px', fontSize: '0.8rem' }}
                          onClick={() => handlePull(m.id)}
                        >
                          &#11015; 다운로드
                        </button>
                      )}
                      {ps?.active && (
                        <div className="pull-progress">
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                            <div className="progress-bar" style={{ height: 6, flex: 1 }}>
                              <div className="progress-fill" style={{ width: `${ps.pct}%`, transition: 'width 0.3s' }} />
                            </div>
                            <button
                              className="btn btn-secondary"
                              style={{ padding: '1px 7px', fontSize: '0.75rem', lineHeight: 1.6, flexShrink: 0 }}
                              onClick={() => handleCancelPull(m.id)}
                              title="다운로드 취소"
                            >
                              취소
                            </button>
                          </div>
                          <span style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>
                            {ps.status}{ps.pct > 0 ? ` ${ps.pct}%` : ''}
                          </span>
                        </div>
                      )}
                      {ps && !ps.active && ps.pct === 100 && (
                        <span style={{ fontSize: '0.8rem', color: 'var(--teal)' }}>&#10003; 설치 완료</span>
                      )}
                      {ps?.error && (
                        <span
                          style={{ fontSize: '0.8rem', color: '#dc2626', cursor: 'pointer' }}
                          title={ps.error}
                          onClick={() => handlePull(m.id)}
                        >
                          &#10005; 재시도
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
              {models.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--ink3)' }}>모델 정보를 불러오는 중...</td></tr>
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
            {PIPELINES.map(p => (
              <button
                key={p.id}
                className="btn btn-primary"
                onClick={() => handleOptimize(p.id)}
                disabled={!!optProgress}
              >
                {p.label}
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
