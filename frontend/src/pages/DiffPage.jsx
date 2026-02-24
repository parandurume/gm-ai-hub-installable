import { useState, useEffect } from 'react'
import { fetchJSON, postJSON, API } from '../utils/api'
import { useToast } from '../hooks/useToast'

export default function DiffPage() {
  const [files, setFiles] = useState([])
  const [pathA, setPathA] = useState('')
  const [pathB, setPathB] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  useEffect(() => {
    fetchJSON(API.documents).then(d => setFiles(d?.files || [])).catch(() => {})
  }, [])

  async function handleCompare() {
    if (!pathA || !pathB) { toast('두 파일을 모두 선택하세요', 'warning'); return }
    if (pathA === pathB) { toast('서로 다른 파일을 선택하세요', 'warning'); return }
    setLoading(true)
    try {
      const data = await postJSON(API.diff, { path_a: pathA, path_b: pathB })
      setResult(data)
      toast('비교 완료', 'success')
    } catch {
      toast('비교 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  function renderDiffLine(line, i) {
    let cls = ''
    if (line.startsWith('+')) cls = 'diff-add'
    else if (line.startsWith('-')) cls = 'diff-del'
    else if (line.startsWith('@@')) cls = 'diff-hunk'
    return <div key={i} className={`diff-line ${cls}`}>{line}</div>
  }

  return (
    <div className="page-diff">
      <h2>문서 비교</h2>

      <div className="form-row" style={{ marginBottom: 16 }}>
        <div className="form-group" style={{ flex: 1 }}>
          <label>문서 A</label>
          <select value={pathA} onChange={e => setPathA(e.target.value)}>
            <option value="">선택...</option>
            {files.map(f => (
              <option key={f.path} value={f.path}>{f.filename}</option>
            ))}
          </select>
        </div>
        <div className="form-group" style={{ flex: 1 }}>
          <label>문서 B</label>
          <select value={pathB} onChange={e => setPathB(e.target.value)}>
            <option value="">선택...</option>
            {files.map(f => (
              <option key={f.path} value={f.path}>{f.filename}</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 2 }}>
          <button className="btn btn-primary" onClick={handleCompare} disabled={loading}>
            {loading ? '비교 중...' : '비교'}
          </button>
        </div>
      </div>

      {result ? (
        <div>
          {result.number_changes?.length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-header">수치 변경</div>
              <div className="card-body">
                <table className="table">
                  <thead>
                    <tr><th>항목</th><th>이전</th><th>이후</th><th>변화</th></tr>
                  </thead>
                  <tbody>
                    {result.number_changes.map((c, i) => (
                      <tr key={i}>
                        <td>{c.label || '—'}</td>
                        <td>{c.old_value}</td>
                        <td>{c.new_value}</td>
                        <td>
                          <span className={`badge ${c.change > 0 ? 'badge-success' : c.change < 0 ? 'badge-error' : 'badge-info'}`}>
                            {c.change > 0 ? '+' : ''}{c.change}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="card">
            <div className="card-header">텍스트 비교</div>
            <div className="card-body diff-view">
              {(result.diff || result.unified_diff || '').split('\n').map(renderDiffLine)}
            </div>
          </div>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: 80, color: 'var(--ink3)' }}>
          두 문서를 선택한 후 비교 버튼을 클릭하세요
        </div>
      )}
    </div>
  )
}
