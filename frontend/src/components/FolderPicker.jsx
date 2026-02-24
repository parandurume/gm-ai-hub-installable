import { useState, useEffect, useCallback } from 'react'
import { fetchJSON, API } from '../utils/api'

/**
 * FolderPicker — 서버 파일시스템 탐색 모달.
 *
 * Props:
 *   open        — 모달 표시 여부
 *   onClose     — 닫기 콜백
 *   onSelect    — (fullPath: string) => void  — 경로 선택 콜백
 *   mode        — "folder" | "save"  (save 모드에서는 파일명 입력 가능)
 *   defaultName — save 모드 기본 파일명 (예: "계획서.hwpx")
 */
export default function FolderPicker({ open, onClose, onSelect, mode = 'save', defaultName = '' }) {
  const [currentPath, setCurrentPath] = useState('')
  const [parentPath, setParentPath] = useState(null)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [fileName, setFileName] = useState(defaultName)

  const browse = useCallback(async (path) => {
    setLoading(true)
    setError('')
    try {
      const params = path ? `?path=${encodeURIComponent(path)}` : ''
      const data = await fetchJSON(`${API.filesystemBrowse}${params}`)
      setCurrentPath(data.path || '')
      setParentPath(data.parent ?? null)
      setItems(data.items || [])
      if (data.error) setError(data.error)
    } catch {
      setError('디렉토리를 불러올 수 없습니다')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) {
      browse('')
      setFileName(defaultName)
    }
  }, [open, browse, defaultName])

  if (!open) return null

  function handleItemClick(item) {
    if (item.is_dir) {
      browse(item.path)
    } else {
      // Clicking a file in save mode → use its name
      if (mode === 'save') {
        setFileName(item.name)
      }
    }
  }

  function handleSelect() {
    if (mode === 'save') {
      const name = fileName.trim()
      if (!name) return
      // Combine current directory + filename
      const sep = currentPath.includes('/') ? '/' : '\\'
      const full = currentPath ? `${currentPath}${sep}${name}` : name
      onSelect(full)
    } else {
      onSelect(currentPath)
    }
    onClose()
  }

  function handleGoUp() {
    if (parentPath !== null) {
      browse(parentPath)
    } else {
      // Go to drive list (Windows) or root
      browse('')
    }
  }

  const dirs = items.filter(i => i.is_dir)
  const files = mode === 'save' ? items.filter(i => !i.is_dir) : []

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="folder-picker-modal" onClick={e => e.stopPropagation()}>
        <div className="fp-header">
          <div className="fp-title">{mode === 'save' ? '저장 위치 선택' : '폴더 선택'}</div>
          <button className="fp-close" onClick={onClose} aria-label="닫기">&times;</button>
        </div>

        <div className="fp-breadcrumb">
          <button className="fp-nav-btn" onClick={handleGoUp} disabled={!currentPath} title="상위 폴더">
            &larr;
          </button>
          <div className="fp-path">{currentPath || '내 컴퓨터'}</div>
        </div>

        {error && <div className="fp-error">{error}</div>}

        <div className="fp-list">
          {loading ? (
            <div className="fp-loading"><div className="spinner" /></div>
          ) : (
            <>
              {dirs.length === 0 && files.length === 0 && (
                <div className="fp-empty">비어 있는 폴더입니다</div>
              )}
              {dirs.map(item => (
                <div
                  key={item.path}
                  className="fp-item fp-folder"
                  onClick={() => handleItemClick(item)}
                  onDoubleClick={() => handleItemClick(item)}
                >
                  <span className="fp-icon">&#128193;</span>
                  <span className="fp-name">{item.name}</span>
                </div>
              ))}
              {files.map(item => (
                <div
                  key={item.path}
                  className={`fp-item fp-file${fileName === item.name ? ' fp-selected' : ''}`}
                  onClick={() => handleItemClick(item)}
                >
                  <span className="fp-icon">&#128196;</span>
                  <span className="fp-name">{item.name}</span>
                </div>
              ))}
            </>
          )}
        </div>

        {mode === 'save' && (
          <div className="fp-filename-row">
            <label>파일명:</label>
            <input
              type="text"
              value={fileName}
              onChange={e => setFileName(e.target.value)}
              placeholder="파일명.hwpx"
            />
          </div>
        )}

        <div className="fp-actions">
          <button className="btn btn-secondary" onClick={onClose}>취소</button>
          <button
            className="btn btn-primary"
            onClick={handleSelect}
            disabled={mode === 'save' && !fileName.trim()}
          >
            {mode === 'save' ? '여기에 저장' : '선택'}
          </button>
        </div>
      </div>
    </div>
  )
}
