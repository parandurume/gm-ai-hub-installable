import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchJSON, postJSON, API } from '../utils/api'
import { useToast } from '../hooks/useToast'

export default function RegulationPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const [online, setOnline] = useState(null)
  const [ocSet, setOcSet] = useState(false)
  const [ocInput, setOcInput] = useState('')
  const [source, setSource] = useState(null)
  const toast = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    fetchJSON(API.regulationStatus)
      .then(d => { setOnline(d.online); setOcSet(d.oc_set) })
      .catch(() => setOnline(false))
  }, [])

  async function handleSetOc(e) {
    e.preventDefault()
    if (!ocInput.trim()) return
    try {
      await postJSON(API.regulationSetOc, { oc: ocInput.trim() })
      setOcSet(true)
      toast('API 키가 설정되었습니다 (이 세션 동안 유효)', 'success')
      // 상태 재확인
      fetchJSON(API.regulationStatus)
        .then(d => { setOnline(d.online); setOcSet(d.oc_set) })
        .catch(() => {})
    } catch {
      toast('API 키 설정 실패', 'error')
    }
  }

  function handleAskAi() {
    const r = results[selected]
    const articleText = r.content || r.text || ''
    const title = r.title || r.law_name || ''
    const article = r.article || ''
    const prompt = `다음 법령 조문에 대해 설명해주세요.\n\n[${title} ${article}]\n${articleText}`
    navigate('/chat', { state: { prefill: prompt } })
  }

  async function handleSearch(e) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    try {
      const params = new URLSearchParams({ q: query, limit: 20 })
      const data = await fetchJSON(`${API.regulationSearch}?${params}`)
      setResults(data?.results || [])
      setSource(data?.source || 'offline')
      if ((data?.results || []).length === 0) toast('검색 결과가 없습니다', 'info')
    } catch {
      toast('검색 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-regulation">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <h2 style={{ margin: 0 }}>법령 검색</h2>
        <span className={`badge ${online ? 'badge-success' : 'badge-gray'}`} style={{ fontSize: '0.75rem' }}>
          {online === null ? '확인 중...' : online ? '온라인' : '오프라인 (로컬 DB)'}
        </span>
        {source && (
          <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>
            {source === 'online' ? '법제처 API' : '로컬 FTS5'}
          </span>
        )}
      </div>

      {/* OC 입력 안내 — 세션에 OC가 없을 때만 표시 */}
      {!ocSet && online === false && (
        <form onSubmit={handleSetOc} className="card" style={{ marginBottom: 16, padding: 16 }}>
          <div style={{ marginBottom: 8, fontSize: '0.88rem', color: 'var(--ink2)' }}>
            <strong>법제처 Open API</strong>를 사용하려면 OC 값을 입력하세요.
            <span style={{ display: 'block', fontSize: '0.78rem', color: 'var(--ink3)', marginTop: 4 }}>
              OC는 이메일 ID입니다 (예: g4c@korea.kr → g4c). 이 값은 앱 종료 시 자동 삭제됩니다.
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              value={ocInput}
              onChange={e => setOcInput(e.target.value)}
              placeholder="OC 값 입력"
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" type="submit">설정</button>
          </div>
        </form>
      )}

      <form className="search-bar" onSubmit={handleSearch}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="법령명 또는 조문 내용을 검색하세요..."
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? '검색 중...' : '검색'}
        </button>
      </form>

      <div className="split-view" style={{ marginTop: 16 }}>
        <div className="panel">
          {results.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>법령명</th>
                  <th>조항</th>
                  <th>점수</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr
                    key={i}
                    className={`file-row ${selected === i ? 'active' : ''}`}
                    onClick={() => setSelected(i)}
                  >
                    <td>{r.title || r.law_name || '—'}</td>
                    <td>{r.article || ''}</td>
                    <td><span className="badge badge-info">{r.score?.toFixed(2)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--ink3)' }}>
              법령명, 키워드 등을 검색하세요
            </div>
          )}
        </div>
        <div className="panel">
          {selected !== null && results[selected] ? (
            <div className="preview-pane">
              <div className="preview-header">{results[selected].title || results[selected].law_name}</div>
              <div className="preview-body" style={{ whiteSpace: 'pre-wrap' }}>
                {results[selected].content || results[selected].text || JSON.stringify(results[selected], null, 2)}
              </div>
              <button className="btn btn-secondary" onClick={handleAskAi} style={{ marginTop: 12 }}>
                AI에게 물어보기
              </button>
            </div>
          ) : (
            <div className="preview-empty">
              <span style={{ fontSize: 48 }}>{'⚖️'}</span>
              <span>검색 결과를 클릭하면 내용이 표시됩니다</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
