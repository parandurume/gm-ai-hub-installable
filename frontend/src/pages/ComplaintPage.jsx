import { useState } from 'react'
import { postJSON, API } from '../utils/api'
import ModelSelector from '../components/ModelSelector'
import ThinkingPanel from '../components/ThinkingPanel'
import { useToast } from '../hooks/useToast'

export default function ComplaintPage() {
  const [text, setText] = useState('')
  const [model, setModel] = useState(null)
  const [classification, setClassification] = useState(null)
  const [draft, setDraft] = useState(null)
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  async function handleClassify() {
    if (!text.trim()) { toast('민원 내용을 입력하세요', 'warning'); return }
    setLoading(true)
    try {
      const data = await postJSON(API.complaintClassify, { text, model })
      setClassification(data)
      toast('분류 완료', 'success')
    } catch {
      toast('분류 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function handleDraft() {
    if (!text.trim()) { toast('민원 내용을 입력하세요', 'warning'); return }
    setLoading(true)
    try {
      const data = await postJSON(API.complaintDraft, { text, model })
      setDraft(data)
      toast('답변 초안 생성 완료', 'success')
    } catch {
      toast('답변 생성 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-complaint">
      <h2>민원 답변</h2>

      <div className="split-view">
        <div className="split-left">
          <div className="form-group">
            <label>민원 내용</label>
            <textarea
              rows={12}
              value={text}
              onChange={e => setText(e.target.value)}
              placeholder="민원인의 민원 내용을 입력하세요..."
            />
          </div>

          <div className="form-group">
            <label>AI 모델</label>
            <ModelSelector value={model} onChange={setModel} task="complaint_resp" />
          </div>

          <div className="form-actions">
            <button className="btn btn-secondary" onClick={handleClassify} disabled={loading}>
              {loading ? '처리 중...' : '민원 분류'}
            </button>
            <button className="btn btn-primary" onClick={handleDraft} disabled={loading}>
              {loading ? '처리 중...' : 'AI 답변 초안'}
            </button>
          </div>

          {classification && (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-header">분류 결과</div>
              <div className="card-body">
                <div className="stat-row">
                  <span>카테고리</span>
                  <span className="badge badge-info">{classification.category}</span>
                </div>
                {classification.department && (
                  <div className="stat-row">
                    <span>담당부서</span>
                    <span>{classification.department}</span>
                  </div>
                )}
                {classification.urgency && (
                  <div className="stat-row">
                    <span>긴급도</span>
                    <span className={`badge ${classification.urgency === 'high' ? 'badge-error' : 'badge-warning'}`}>
                      {classification.urgency}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="split-right">
          {draft?.thinking && <ThinkingPanel content={draft.thinking} />}
          {draft ? (
            <div className="preview-pane">
              <div className="preview-header">
                AI 답변 초안
                {draft.path && <span style={{ fontSize: '0.8rem', color: 'var(--ink3)' }}> - {draft.path}</span>}
              </div>
              <div className="preview-body" style={{ whiteSpace: 'pre-wrap' }}>{draft.response || draft.text || JSON.stringify(draft, null, 2)}</div>
            </div>
          ) : (
            <div className="preview-empty">
              <span style={{ fontSize: 48 }}>{'📨'}</span>
              <span>민원 내용을 입력하고 답변 초안을 생성하세요</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
