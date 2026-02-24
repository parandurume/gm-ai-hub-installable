import { useState } from 'react'
import { fetchJSON, API } from '../utils/api'
import { useToast } from '../hooks/useToast'

export default function RegulationPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  async function handleSearch(e) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    try {
      const params = new URLSearchParams({ q: query, limit: 20 })
      const data = await fetchJSON(`${API.regulationSearch}?${params}`)
      setResults(data?.results || [])
      if ((data?.results || []).length === 0) toast('검색 결과가 없습니다', 'info')
    } catch {
      toast('검색 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-regulation">
      <h2>법령 검색</h2>

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
        <div className="split-left">
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
        <div className="split-right">
          {selected !== null && results[selected] ? (
            <div className="preview-pane">
              <div className="preview-header">{results[selected].title || results[selected].law_name}</div>
              <div className="preview-body" style={{ whiteSpace: 'pre-wrap' }}>
                {results[selected].content || results[selected].text || JSON.stringify(results[selected], null, 2)}
              </div>
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
