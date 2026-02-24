import { useState, useCallback } from 'react'
import { fetchJSON, API } from '../utils/api'
import HwpxPreview from '../components/HwpxPreview'
import { useToast } from '../hooks/useToast'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('hybrid')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const toast = useToast()
  const handlePreviewError = useCallback(() => toast('미리보기 실패', 'error'), [toast])

  async function handleSearch(e) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    try {
      const params = new URLSearchParams({ q: query, mode, limit: 20 })
      const data = await fetchJSON(`${API.search}?${params}`)
      setResults(data?.results || [])
      if ((data?.results || []).length === 0) toast('검색 결과가 없습니다', 'info')
    } catch {
      toast('검색 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-search">
      <h2>문서 검색</h2>

      <form className="search-bar" onSubmit={handleSearch}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="검색어를 입력하세요..."
          style={{ flex: 1 }}
        />
        <select value={mode} onChange={e => setMode(e.target.value)}>
          <option value="hybrid">하이브리드</option>
          <option value="keyword">키워드 (FTS5)</option>
          <option value="semantic">의미 검색</option>
        </select>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? '검색 중...' : '검색'}
        </button>
      </form>

      <div className="split-view" style={{ marginTop: 16 }}>
        <div className="split-left">
          {results.length > 0 && (
            <table className="table">
              <thead>
                <tr>
                  <th>파일명</th>
                  <th>점수</th>
                  <th>미리보기</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr
                    key={i}
                    className={`file-row ${selected === r.path ? 'active' : ''}`}
                    onClick={() => setSelected(r.path)}
                  >
                    <td>{r.filename || r.path?.split('/').pop()}</td>
                    <td><span className="badge badge-info">{r.score?.toFixed(2)}</span></td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--ink3)' }}>
                      {r.snippet ? r.snippet.slice(0, 80) + '...' : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {results.length === 0 && !loading && (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--ink3)' }}>
              검색어를 입력하고 검색 버튼을 클릭하세요
            </div>
          )}
        </div>
        <div className="split-right">
          <HwpxPreview filePath={selected} onError={handlePreviewError} />
        </div>
      </div>
    </div>
  )
}
