/** 학습 샘플 관리 컴포넌트 — HWPX → MIPROv2 학습 예시 변환 */
import { useState, useEffect } from 'react'
import { fetchJSON, postJSON, API } from '../utils/api'
import { useToast } from '../hooks/useToast'

const PIPELINES = ['draft', 'docent', 'complaint', 'meeting']
const PIPELINE_LABELS = {
  draft: '기안문',
  docent: '도슨트',
  complaint: '민원',
  meeting: '회의록',
}
const DOC_TYPES = ['일반기안', '협조전', '보고서', '계획서', '결과보고서', '회의록', '민원답변']

export default function SampleManager() {
  const [pipeline, setPipeline] = useState('draft')
  const [files, setFiles] = useState([])
  const [candidates, setCandidates] = useState([])
  const [scanning, setScanning] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [selected, setSelected] = useState(new Set())
  const toast = useToast()

  useEffect(() => {
    loadPending()
  }, [pipeline])

  async function loadPending() {
    try {
      const data = await fetchJSON(`${API.samplesPending}?pipeline=${pipeline}`)
      if (data.pending?.length > 0) {
        setCandidates(data.pending)
        setFiles([])
      } else {
        setCandidates([])
        handleScan()
      }
    } catch {
      setCandidates([])
    }
  }

  async function handleScan() {
    setScanning(true)
    try {
      const data = await fetchJSON(`${API.samplesScan}?pipeline=${pipeline}`)
      setFiles(data.files || [])
      if (data.count === 0) {
        toast(`data/samples/${pipeline}/ 폴더에 .hwpx 파일을 넣어주세요`, 'info')
      }
    } catch {
      toast('스캔 실패', 'error')
    } finally {
      setScanning(false)
    }
  }

  async function handleExtract() {
    setExtracting(true)
    try {
      const data = await postJSON(API.samplesExtract, { pipeline })
      setCandidates(data.candidates || [])
      setFiles([])
      if (data.errors?.length > 0) {
        toast(`${data.errors.length}개 파일 추출 실패`, 'warning')
      }
      if (data.candidates?.length > 0) {
        toast(`${data.candidates.length}개 후보 생성 완료`, 'success')
      }
    } catch {
      toast('추출 실패', 'error')
    } finally {
      setExtracting(false)
    }
  }

  function updateCandidate(idx, field, value) {
    setCandidates(prev => {
      const next = [...prev]
      next[idx] = { ...next[idx], [field]: value }
      return next
    })
  }

  function toggleSelect(idx) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
  }

  function selectAll() {
    if (selected.size === candidates.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(candidates.map((_, i) => i)))
    }
  }

  async function handleApprove() {
    const toApprove = candidates.filter((_, i) => selected.has(i))
    if (toApprove.length === 0) {
      toast('승인할 항목을 선택하세요', 'warning')
      return
    }
    try {
      const result = await postJSON(API.samplesApprove, {
        pipeline,
        examples: toApprove,
      })
      toast(`${result.added}개 학습 예시 저장 완료`, 'success')
      setCandidates(prev => prev.filter((_, i) => !selected.has(i)))
      setSelected(new Set())
    } catch {
      toast('저장 실패', 'error')
    }
  }

  async function handleRejectSelected() {
    const toReject = candidates.filter((_, i) => selected.has(i))
    const filenames = toReject.map(c => c.filename).filter(Boolean)
    try {
      await fetchJSON(API.samplesReject, {
        method: 'DELETE',
        body: JSON.stringify({ pipeline, filenames }),
      })
      setCandidates(prev => prev.filter((_, i) => !selected.has(i)))
      setSelected(new Set())
      toast('선택 항목 제거 완료', 'info')
    } catch {
      toast('제거 실패', 'error')
    }
  }

  return (
    <div className="sample-manager">
      <h3>HWPX 샘플 → 학습 데이터</h3>
      <p style={{ color: 'var(--ink3)', fontSize: '0.85rem', marginBottom: 16 }}>
        <code>data/samples/{'{pipeline}'}/</code> 폴더에 기존 HWPX 문서를 넣으면,
        AI가 문서 유형·제목·지시문을 자동 분석합니다. 검토 후 승인하면 MIPROv2 학습 데이터로 사용됩니다.
      </p>

      {/* Pipeline selector */}
      <div className="form-group" style={{ marginBottom: 16 }}>
        <label>파이프라인</label>
        <div style={{ display: 'flex', gap: 6 }}>
          {PIPELINES.map(p => (
            <button
              key={p}
              className={`btn ${pipeline === p ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => { setPipeline(p); setSelected(new Set()) }}
              style={{ fontSize: '0.85rem' }}
            >{PIPELINE_LABELS[p]}</button>
          ))}
        </div>
      </div>

      {/* File scan results */}
      {candidates.length === 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>샘플 파일 ({files.length}개)</span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn btn-secondary" onClick={handleScan} disabled={scanning} style={{ fontSize: '0.8rem' }}>
                {scanning ? '스캔 중...' : '다시 스캔'}
              </button>
              {files.length > 0 && (
                <button className="btn btn-primary" onClick={handleExtract} disabled={extracting} style={{ fontSize: '0.8rem' }}>
                  {extracting ? 'AI 분석 중...' : `전체 추출 (${files.length}개)`}
                </button>
              )}
            </div>
          </div>
          <div className="card-body">
            {files.length === 0 ? (
              <p style={{ color: 'var(--ink3)', textAlign: 'center', padding: 20 }}>
                data/samples/{pipeline}/ 폴더에 .hwpx 파일을 넣어주세요
              </p>
            ) : (
              <table className="table">
                <thead>
                  <tr><th>파일명</th><th>크기</th><th>상태</th></tr>
                </thead>
                <tbody>
                  {files.map((f, i) => (
                    <tr key={i}>
                      <td>{f.filename}</td>
                      <td>{f.size_kb} KB</td>
                      <td>
                        <span className={`badge ${f.status === 'pending' ? 'badge-warning' : 'badge-info'}`}>
                          {f.status === 'pending' ? '추출 대기' : '미처리'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Candidate review */}
      {candidates.length > 0 && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontWeight: 600 }}>검토 대기 ({candidates.length}개)</span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn btn-secondary" onClick={selectAll} style={{ fontSize: '0.8rem' }}>
                {selected.size === candidates.length ? '전체 해제' : '전체 선택'}
              </button>
              <button className="btn btn-primary" onClick={handleApprove} disabled={selected.size === 0} style={{ fontSize: '0.8rem' }}>
                선택 승인 ({selected.size})
              </button>
              <button className="btn btn-secondary" onClick={handleRejectSelected} disabled={selected.size === 0}
                style={{ fontSize: '0.8rem', color: 'var(--red, #d32)' }}>
                선택 제거
              </button>
            </div>
          </div>

          {candidates.map((c, idx) => (
            <CandidateCard
              key={idx}
              candidate={c}
              pipeline={pipeline}
              selected={selected.has(idx)}
              onToggle={() => toggleSelect(idx)}
              onChange={(field, val) => updateCandidate(idx, field, val)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function CandidateCard({ candidate, pipeline, selected, onToggle, onChange }) {
  const [expanded, setExpanded] = useState(false)

  if (candidate.error) {
    return (
      <div className="card" style={{ marginBottom: 8, borderColor: 'var(--red, #d32)', opacity: 0.7 }}>
        <div className="card-body" style={{ padding: 12 }}>
          <strong>{candidate.filename}</strong>
          <span style={{ color: 'var(--red, #d32)', marginLeft: 8 }}>{candidate.error}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="card" style={{ marginBottom: 10, borderColor: selected ? 'var(--teal)' : undefined }}>
      <div className="card-body" style={{ padding: 12 }}>
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <input type="checkbox" checked={selected} onChange={onToggle} />
          <span style={{ fontSize: '0.8rem', color: 'var(--ink3)' }}>{candidate.filename}</span>
          <button
            className="btn btn-secondary"
            onClick={() => setExpanded(!expanded)}
            style={{ fontSize: '0.75rem', marginLeft: 'auto', padding: '2px 8px' }}
          >
            {expanded ? '본문 접기' : '본문 보기'}
          </button>
        </div>

        {/* Editable fields — pipeline-specific */}
        {pipeline === 'draft' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 8 }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>문서 유형</label>
              <select value={candidate.doc_type || ''} onChange={e => onChange('doc_type', e.target.value)} style={{ width: '100%' }}>
                {DOC_TYPES.map(dt => <option key={dt} value={dt}>{dt}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>제목</label>
              <input type="text" value={candidate.subject || ''} onChange={e => onChange('subject', e.target.value)} style={{ width: '100%' }} />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>지시문</label>
              <input type="text" value={candidate.instruction || ''} onChange={e => onChange('instruction', e.target.value)} style={{ width: '100%' }} />
            </div>
          </div>
        )}

        {pipeline === 'docent' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>사업/교육명</label>
              <input type="text" value={candidate.title || ''} onChange={e => onChange('title', e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>대상 인원</label>
              <input type="number" value={candidate.target_count || 10} onChange={e => onChange('target_count', Number(e.target.value))} style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>기간 (개월)</label>
              <input type="number" value={candidate.months || 6} onChange={e => onChange('months', Number(e.target.value))} style={{ width: '100%' }} />
            </div>
          </div>
        )}

        {pipeline === 'complaint' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>민원 유형</label>
              <input type="text" value={candidate.expected_category || ''} onChange={e => onChange('expected_category', e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>담당 부서</label>
              <input type="text" value={candidate.expected_department || ''} onChange={e => onChange('expected_department', e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>긴급도</label>
              <select value={candidate.expected_urgency || 'medium'} onChange={e => onChange('expected_urgency', e.target.value)} style={{ width: '100%' }}>
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>민원 요약</label>
              <input type="text" value={candidate.complaint_summary || ''} onChange={e => onChange('complaint_summary', e.target.value)} style={{ width: '100%' }} />
            </div>
          </div>
        )}

        {pipeline === 'meeting' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>회의 제목</label>
              <input type="text" value={candidate.title || ''} onChange={e => onChange('title', e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>일자</label>
              <input type="text" value={candidate.date || ''} onChange={e => onChange('date', e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--ink3)' }}>참석자</label>
              <input type="text" value={candidate.attendees || ''} onChange={e => onChange('attendees', e.target.value)} style={{ width: '100%' }} />
            </div>
          </div>
        )}

        {/* Expandable body preview */}
        {expanded && (
          <div style={{ marginTop: 10, padding: 10, background: 'var(--bg2, #f5f5f5)', borderRadius: 4, maxHeight: 300, overflow: 'auto' }}>
            <pre style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap', margin: 0 }}>
              {candidate.expected_body || candidate.expected_summary || '(본문 없음)'}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
