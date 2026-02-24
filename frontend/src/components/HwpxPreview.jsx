import { useState, useEffect } from 'react'

export default function HwpxPreview({ filePath, onError }) {
  const [html, setHtml] = useState('')
  const [loading, setLoading] = useState(false)
  const [meta, setMeta] = useState(null)

  useEffect(() => {
    if (!filePath) return
    setLoading(true)
    const params = new URLSearchParams({ path: filePath })

    Promise.all([
      fetch(`/api/documents/preview?${params}`).then(r => r.text()),
      fetch(`/api/documents/meta?${params}`).then(r => r.ok ? r.json() : null),
    ])
      .then(([previewHtml, metadata]) => {
        setHtml(previewHtml)
        setMeta(metadata)
      })
      .catch(err => onError?.(err))
      .finally(() => setLoading(false))
  }, [filePath])

  if (!filePath) return (
    <div className="preview-empty">
      <span style={{ fontSize: 48 }}>{'\uD83D\uDCD7'}</span>
      <span>파일을 선택하면 미리보기가 표시됩니다</span>
    </div>
  )

  if (loading) return <div className="preview-loading"><span className="spinner" /> 로딩 중...</div>

  return (
    <div>
      {meta && (
        <div className="preview-meta-bar">
          {meta.fiscal_year && <span className="meta-chip teal">{'\uD83D\uDCC5'} {meta.fiscal_year}년</span>}
          {meta.budget && <span className="meta-chip amber">{'\uD83D\uDCB0'} {meta.budget}</span>}
          {meta.date_scan?.passed === false && <span className="meta-chip red">{'\u26A0\uFE0F'} 연도 검토 필요</span>}
        </div>
      )}
      <div className="hwpx-preview-body" dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )
}
