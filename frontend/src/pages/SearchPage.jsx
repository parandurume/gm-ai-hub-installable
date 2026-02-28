import { useState, useCallback } from 'react'
import { fetchJSON, API } from '../utils/api'
import HwpxPreview from '../components/HwpxPreview'
import { useToast } from '../hooks/useToast'

const MODE_INFO = {
  hybrid: {
    label: '하이브리드',
    desc: '키워드 + 의미 검색을 결합하여 가장 정확한 결과를 제공합니다.',
    icon: '\u2728',
  },
  keyword: {
    label: '키워드 (FTS5)',
    desc: '입력한 단어가 정확히 포함된 문서를 빠르게 검색합니다.',
    icon: '\uD83D\uDD24',
  },
  semantic: {
    label: '의미 검색',
    desc: 'AI가 문맥과 의미를 이해하여 관련 문서를 찾습니다. (Ollama 필요)',
    icon: '\uD83E\uDDE0',
  },
}

const SEARCH_TIPS = [
  { query: '"예산 편성"', desc: '정확한 문구를 검색하려면 따옴표를 사용하세요' },
  { query: '회의 AND 결과', desc: '여러 키워드를 모두 포함하는 문서를 찾습니다' },
  { query: '민원 답변', desc: '관련 키워드로 문서를 검색합니다' },
]

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('hybrid')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const toast = useToast()
  const handlePreviewError = useCallback(() => toast('미리보기 실패', 'error'), [toast])

  async function handleSearch(e) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setSearched(true)
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

  function handleTipClick(tip) {
    setQuery(tip)
  }

  return (
    <div className="page-search">
      <h2>문서 검색</h2>

      {/* 검색 모드 안내 */}
      <div className="search-mode-bar">
        {Object.entries(MODE_INFO).map(([key, info]) => (
          <button
            key={key}
            className={`search-mode-chip ${mode === key ? 'active' : ''}`}
            onClick={() => setMode(key)}
            title={info.desc}
          >
            <span>{info.icon}</span>
            <span>{info.label}</span>
          </button>
        ))}
        <span className="search-mode-help">{MODE_INFO[mode].desc}</span>
      </div>

      <form className="search-bar" onSubmit={handleSearch}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="검색어를 입력하세요... (예: 예산 편성, 민원 답변)"
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? '검색 중...' : '검색'}
        </button>
      </form>

      {/* 검색 전 가이드 */}
      {!searched && results.length === 0 && (
        <div className="search-guide">
          <div className="search-guide-main">
            <div className="search-guide-icon">{'\uD83D\uDD0D'}</div>
            <h3>작업 폴더의 문서를 검색합니다</h3>
            <p className="search-guide-desc">
              작업 폴더에 저장된 <strong>HWPX, PDF, DOCX, TXT</strong> 파일의 내용을 검색할 수 있습니다.
              검색 결과에서 파일을 클릭하면 오른쪽에 미리보기가 표시됩니다.
            </p>

            <div className="search-guide-steps">
              <div className="search-step">
                <div className="search-step-num">1</div>
                <div>
                  <strong>검색 모드 선택</strong>
                  <p>위의 모드 버튼에서 검색 방식을 선택합니다. 기본값 "하이브리드"가 가장 정확합니다.</p>
                </div>
              </div>
              <div className="search-step">
                <div className="search-step-num">2</div>
                <div>
                  <strong>검색어 입력</strong>
                  <p>찾고 싶은 키워드나 문장을 입력하고 검색 버튼을 클릭하거나 Enter를 누릅니다.</p>
                </div>
              </div>
              <div className="search-step">
                <div className="search-step-num">3</div>
                <div>
                  <strong>결과 확인</strong>
                  <p>검색 결과 목록에서 파일을 클릭하면 오른쪽에 문서 미리보기가 표시됩니다.</p>
                </div>
              </div>
            </div>

            <div className="search-tips">
              <span className="search-tips-label">검색 예시:</span>
              {SEARCH_TIPS.map((tip, i) => (
                <button
                  key={i}
                  className="search-tip-chip"
                  onClick={() => handleTipClick(tip.query)}
                  title={tip.desc}
                >
                  {tip.query}
                </button>
              ))}
            </div>
          </div>

          <div className="search-guide-sidebar">
            <div className="search-guide-note">
              <strong>{'\uD83D\uDCC1'} 문서가 검색되지 않나요?</strong>
              <p>
                작업 폴더에 문서 파일이 있어야 검색 가능합니다.
                <strong> 문서 관리</strong> 페이지에서 파일을 업로드하거나,
                <strong> 설정</strong>에서 작업 폴더 경로를 확인하세요.
              </p>
            </div>
            <div className="search-guide-note">
              <strong>{'\uD83E\uDDE0'} 의미 검색이란?</strong>
              <p>
                AI 임베딩 모델(nomic-embed-text)이 문서의 의미를 분석하여,
                정확한 키워드가 없어도 관련 문서를 찾아줍니다.
                Ollama가 실행 중이어야 사용 가능합니다.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 검색 후 결과 */}
      {(searched || results.length > 0) && (
        <div className="split-view" style={{ marginTop: 16 }}>
          <div className="panel">
            {results.length > 0 && (
              <>
                <div className="panel-header">
                  <span>검색 결과 ({results.length}건)</span>
                  <span className="search-mode-badge">{MODE_INFO[mode].icon} {MODE_INFO[mode].label}</span>
                </div>
                <div className="panel-body" style={{ padding: 0 }}>
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
                </div>
              </>
            )}
            {searched && results.length === 0 && !loading && (
              <div style={{ textAlign: 'center', padding: 60, color: 'var(--ink3)' }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>{'\uD83D\uDDC2\uFE0F'}</div>
                <p>"{query}"에 대한 검색 결과가 없습니다</p>
                <p style={{ fontSize: '0.85rem', marginTop: 8 }}>
                  다른 키워드로 시도하거나, 작업 폴더에 문서가 있는지 확인하세요.
                </p>
              </div>
            )}
          </div>
          <div className="panel">
            <HwpxPreview filePath={selected} onError={handlePreviewError} />
          </div>
        </div>
      )}
    </div>
  )
}
