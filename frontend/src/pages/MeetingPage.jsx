import { useState } from 'react'
import { postJSON, API } from '../utils/api'
import ModelSelector from '../components/ModelSelector'
import ThinkingPanel from '../components/ThinkingPanel'
import { useToast } from '../hooks/useToast'

export default function MeetingPage() {
  const [form, setForm] = useState({
    title: '',
    date: new Date().toISOString().slice(0, 10),
    attendees: '',
    content: '',
    model: null,
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  function updateField(key, val) {
    setForm(f => ({ ...f, [key]: val }))
  }

  async function handleGenerate() {
    if (!form.content.trim()) { toast('회의 내용을 입력하세요', 'warning'); return }
    setLoading(true)
    try {
      const data = await postJSON(API.meeting, {
        title: form.title,
        date: form.date,
        attendees: form.attendees.split(',').map(s => s.trim()).filter(Boolean),
        content: form.content,
        model: form.model,
      })
      setResult(data)
      toast('회의록 생성 완료', 'success')
    } catch {
      toast('회의록 생성 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-meeting">
      <h2>회의록 작성</h2>

      <div className="split-view">
        <div className="split-left">
          <div className="form-group">
            <label>회의 제목</label>
            <input
              type="text"
              value={form.title}
              onChange={e => updateField('title', e.target.value)}
              placeholder="예: 2026년 상반기 AI 도입 추진회의"
            />
          </div>

          <div className="form-row">
            <div className="form-group" style={{ flex: 1 }}>
              <label>일자</label>
              <input type="date" value={form.date} onChange={e => updateField('date', e.target.value)} />
            </div>
            <div className="form-group" style={{ flex: 2 }}>
              <label>참석자 (쉼표 구분)</label>
              <input
                type="text"
                value={form.attendees}
                onChange={e => updateField('attendees', e.target.value)}
                placeholder="홍길동, 김철수, 이영희"
              />
            </div>
          </div>

          <div className="form-group">
            <label>회의 내용 / 메모</label>
            <textarea
              rows={10}
              value={form.content}
              onChange={e => updateField('content', e.target.value)}
              placeholder="회의 중 논의된 내용을 자유롭게 입력하세요..."
            />
          </div>

          <div className="form-group">
            <label>AI 모델</label>
            <ModelSelector value={form.model} onChange={v => updateField('model', v)} task="meeting_minutes" />
          </div>

          <button className="btn btn-primary" onClick={handleGenerate} disabled={loading}>
            {loading ? 'AI 요약 중...' : 'AI 회의록 생성'}
          </button>
        </div>

        <div className="split-right">
          {result?.thinking && <ThinkingPanel content={result.thinking} />}
          {result ? (
            <div className="preview-pane">
              <div className="preview-header">
                AI 회의록
                {result.path && <span style={{ fontSize: '0.8rem', color: 'var(--ink3)' }}> - {result.path}</span>}
              </div>
              <div className="preview-body" style={{ whiteSpace: 'pre-wrap' }}>{result.summary || result.text || JSON.stringify(result, null, 2)}</div>
            </div>
          ) : (
            <div className="preview-empty">
              <span style={{ fontSize: 48 }}>{'📋'}</span>
              <span>회의 내용을 입력하고 AI 생성 버튼을 클릭하세요</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
