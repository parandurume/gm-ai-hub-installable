import { useState, useEffect, useCallback } from 'react'
import { fetchJSON, API } from '../utils/api'
import FileTable from '../components/FileTable'
import HwpxPreview from '../components/HwpxPreview'
import { useToast } from '../hooks/useToast'

export default function FilesPage() {
  const [files, setFiles] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  /* rerender-memo-with-default-value: Stable callback ref avoids
     creating a new function on each render that would break memo. */
  const handlePreviewError = useCallback(() => toast('미리보기 로드 실패', 'error'), [toast])

  useEffect(() => {
    loadFiles()
  }, [])

  async function loadFiles() {
    setLoading(true)
    try {
      const data = await fetchJSON(API.documents)
      setFiles(data?.files || [])
    } catch {
      toast('파일 목록 로드 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(path) {
    if (!confirm('정말 삭제하시겠습니까?')) return
    try {
      await fetch(`${API.documents}/${encodeURIComponent(path)}`, { method: 'DELETE' })
      toast('삭제 완료', 'success')
      setSelected(null)
      loadFiles()
    } catch {
      toast('삭제 실패', 'error')
    }
  }

  async function handleRebuildIndex() {
    try {
      await fetch(`${API.documents}/index/rebuild`, { method: 'POST' })
      toast('인덱스 재구성 완료', 'success')
    } catch {
      toast('인덱스 재구성 실패', 'error')
    }
  }

  return (
    <div className="page-files">
      <div className="page-header">
        <h2>문서 관리</h2>
        <div className="page-actions">
          <button className="btn btn-secondary" onClick={handleRebuildIndex}>인덱스 재구성</button>
          <button className="btn btn-secondary" onClick={loadFiles}>새로고침</button>
        </div>
      </div>

      <div className="split-view">
        <div className="split-left">
          {loading ? (
            <div className="loading-overlay"><span className="spinner" /> 로딩 중...</div>
          ) : (
            <FileTable files={files} selected={selected} onSelect={setSelected} />
          )}
        </div>
        <div className="split-right">
          <HwpxPreview
            filePath={selected}
            onError={handlePreviewError}
          />
          {selected && (
            <div style={{ padding: '12px', borderTop: '1px solid var(--line)' }}>
              <button className="btn btn-danger" onClick={() => handleDelete(selected)}>삭제</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
