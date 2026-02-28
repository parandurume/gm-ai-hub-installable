import { useState, useEffect, useCallback } from 'react'
import { fetchJSON, postJSON, API } from '../utils/api'
import FileTable from '../components/FileTable'
import PiiSummaryBar from '../components/PiiSummaryBar'
import PiiHeatmapPreview from '../components/PiiHeatmapPreview'
import { useToast } from '../hooks/useToast'

/* rendering-hoist-jsx: Hoist constant outside component to avoid re-creation */
const PII_TYPE_LABELS = {
  '주민등록번호': '주민등록번호',
  '전화번호': '전화번호',
  '이메일': '이메일',
  '주소': '주소',
  '계좌번호': '계좌번호',
  '여권번호': '여권번호',
  '운전면허번호': '운전면허번호',
}

const PII_TYPE_COLORS = {
  '주민등록번호': '#c0392b',
  '전화번호':     '#2980b9',
  '이메일':       '#8e44ad',
  '주소':         '#27ae60',
  '계좌번호':     '#d35400',
  '여권번호':     '#16a085',
  '운전면허번호': '#2c3e50',
}

function PiiBatchSummary({ batchResult }) {
  if (!batchResult) return null
  const { total_files, files_with_pii, type_summary } = batchResult
  return (
    <div className="pii-batch-summary">
      <h4>일괄 스캔 결과: {total_files}개 파일 중 {files_with_pii}개에서 PII 발견</h4>
      <div className="pii-batch-grid">
        {Object.entries(type_summary).map(([type, count]) => (
          <span
            key={type}
            className="pii-type-chip"
            style={{ background: `${PII_TYPE_COLORS[type] || '#555'}1f`, color: PII_TYPE_COLORS[type] || '#555' }}
          >
            {type} {count}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function PiiPage() {
  const [files, setFiles] = useState([])
  const [selected, setSelected] = useState(null)
  const [scanResult, setScanResult] = useState(null)
  const [documentText, setDocumentText] = useState(null)
  const [maskedText, setMaskedText] = useState(null)
  const [showMasked, setShowMasked] = useState(false)
  const [activeIndex, setActiveIndex] = useState(null)
  const [batchResult, setBatchResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const toast = useToast()

  useEffect(() => {
    fetchJSON(API.documents).then(d => setFiles(d?.files || [])).catch(() => {})
  }, [])

  async function handleScan() {
    if (!selected) { toast('파일을 선택하세요', 'warning'); return }
    setLoading(true)
    setScanResult(null)
    setDocumentText(null)
    setMaskedText(null)
    setActiveIndex(null)
    setShowMasked(false)
    try {
      const data = await postJSON(API.piiScan, { path: selected, include_text: true })
      setScanResult(data)
      if (data?.text) setDocumentText(data.text)
      if (data?.masked_text) setMaskedText(data.masked_text)
      if (data?.total_found > 0) {
        toast(`${data.total_found}건의 개인정보 발견`, 'warning')
      } else {
        toast('개인정보가 발견되지 않았습니다', 'success')
      }
    } catch {
      toast('PII 스캔 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function handleMask() {
    if (!selected) { toast('파일을 선택하세요', 'warning'); return }
    setLoading(true)
    try {
      const data = await postJSON(API.piiMask, { path: selected })
      toast(`마스킹 완료: ${data?.path || ''}`, 'success')
    } catch {
      toast('마스킹 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function handleExportReport() {
    if (!scanResult || !selected) return
    setExporting(true)
    try {
      const res = await fetch(API.piiExportReport, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: selected,
          findings: scanResult.findings || [],
          total_found: scanResult.total_found || 0,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const cd = res.headers.get('content-disposition') || ''
      const match = cd.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/)
      const filename = match ? decodeURIComponent(match[1]) : `PII검사보고서_${Date.now()}.hwpx`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
      toast('보고서 다운로드 완료', 'success')
    } catch (e) {
      toast(`보고서 내보내기 실패: ${e.message}`, 'error')
    } finally {
      setExporting(false)
    }
  }

  async function handleBatchScan() {
    if (!files.length) { toast('파일이 없습니다', 'warning'); return }
    setLoading(true)
    setBatchResult(null)
    try {
      const paths = files.map(f => f.path)
      const data = await postJSON(API.piiBatchScan, { paths })
      setBatchResult(data)
      toast(`일괄 스캔 완료: ${data.files_with_pii}/${data.total_files}개 파일에서 PII 발견`, 'info')
    } catch {
      toast('일괄 스캔 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  const findings = scanResult?.findings || []

  return (
    <div className="page-pii">
      <div className="page-header">
        <h2>개인정보(PII) 관리</h2>
        <div className="page-actions">
          <button className="btn btn-secondary btn-sm" onClick={handleExportReport} disabled={!scanResult || exporting}>
            {exporting ? '내보내는 중...' : '보고서 내보내기'}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={handleBatchScan} disabled={loading}>
            일괄 스캔
          </button>
        </div>
      </div>

      <PiiSummaryBar scanResult={scanResult} loading={loading && !!selected} />
      <PiiBatchSummary batchResult={batchResult} />

      <div className="pii-tri-view">
        {/* 좌측: 파일 목록 */}
        <div className="pii-panel">
          <div className="pii-panel-header">문서 목록</div>
          <div className="pii-panel-body">
            <FileTable files={files} selected={selected} onSelect={(path) => {
              setSelected(path)
              setScanResult(null)
              setDocumentText(null)
              setMaskedText(null)
              setActiveIndex(null)
            }} />
          </div>
        </div>

        {/* 중앙: 히트맵 미리보기 */}
        <div className="pii-panel">
          <div className="pii-preview-toolbar">
            <button className="btn btn-primary btn-sm" onClick={handleScan} disabled={loading || !selected}>
              {loading ? '스캔 중...' : 'PII 스캔'}
            </button>
            <button className="btn btn-warning btn-sm" onClick={handleMask} disabled={loading || !selected}>
              PII 마스킹
            </button>
            {documentText && (
              <label className="checkbox-label" style={{ marginLeft: 'auto' }}>
                <input
                  type="checkbox"
                  checked={showMasked}
                  onChange={e => setShowMasked(e.target.checked)}
                />
                마스킹 보기
              </label>
            )}
          </div>
          <div className="pii-panel-body">
            <PiiHeatmapPreview
              text={documentText}
              maskedText={maskedText}
              findings={findings}
              showMasked={showMasked}
              activeIndex={activeIndex}
              onFindingHover={setActiveIndex}
            />
          </div>
        </div>

        {/* 우측: 발견 목록 */}
        <div className="pii-panel">
          <div className="pii-panel-header">발견 목록 ({findings.length})</div>
          <div className="pii-panel-body findings-list">
            {findings.length === 0 && scanResult && (
              <div style={{ padding: 20, textAlign: 'center', color: 'var(--ink3)', fontSize: '0.85rem' }}>
                개인정보가 발견되지 않았습니다
              </div>
            )}
            {findings.map((f, i) => {
              // Build a short context snippet from the original document text
              const snippet = (() => {
                if (!documentText) return null
                const s = f.start ?? 0
                const e = f.end ?? s + (f.value?.length || 6)
                const before = documentText.slice(Math.max(0, s - 18), s)
                const after = documentText.slice(e, e + 18)
                return { before, masked: f.masked_value || f.value || '***', after }
              })()
              return (
                <div
                  key={i}
                  className={`finding-row${activeIndex === i ? ' active' : ''}`}
                  onClick={() => setActiveIndex(i)}
                >
                  <div className="finding-row-top">
                    <span
                      className="finding-type-chip"
                      style={{
                        background: `${PII_TYPE_COLORS[f.type] || '#555'}22`,
                        color: PII_TYPE_COLORS[f.type] || '#555',
                      }}
                    >
                      {PII_TYPE_LABELS[f.type] || f.type}
                    </span>
                    <span className="finding-pos">위치 {f.start}</span>
                  </div>
                  {snippet && (
                    <div className="finding-context">
                      <span className="finding-ctx-text">{snippet.before}</span>
                      <span className="finding-ctx-match" style={{ color: PII_TYPE_COLORS[f.type] || '#c0392b' }}>
                        {snippet.masked}
                      </span>
                      <span className="finding-ctx-text">{snippet.after}</span>
                    </div>
                  )}
                </div>
              )
            })}
            {!scanResult && !loading && (
              <div className="preview-empty" style={{ height: 200 }}>
                <span style={{ fontSize: 36 }}>{'🔒'}</span>
                <span style={{ fontSize: '0.85rem' }}>파일을 선택한 후 PII 스캔을 실행하세요</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
