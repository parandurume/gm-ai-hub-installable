import { useState, useEffect, useRef } from 'react'
import { fetchJSON, postJSON, API } from '../utils/api'
import ModelSelector from '../components/ModelSelector'
import ThinkingPanel from '../components/ThinkingPanel'
import FolderPicker from '../components/FolderPicker'
import GuardSummaryBar from '../components/GuardSummaryBar'
import AnnotatedPreview from '../components/AnnotatedPreview'
import { useToast } from '../hooks/useToast'

const FALLBACK_TEMPLATES = ['일반기안', '협조전', '보고서', '계획서', '결과보고서', '회의록', '민원답변']

const TEMPLATE_ICONS = {
  '일반기안': '📄', '협조전': '🤝', '보고서': '📊',
  '계획서': '📝', '결과보고서': '✅', '회의록': '📋', '민원답변': '📨',
}

function TemplateCards({ templates, value, onChange }) {
  return (
    <div className="template-cards">
      {templates.map(name => (
        <button
          key={name}
          type="button"
          className={`template-card ${value === name ? 'active' : ''}`}
          onClick={() => onChange(value === name ? '' : name)}
        >
          <span className="template-card-icon">{TEMPLATE_ICONS[name] || '📄'}</span>
          <span className="template-card-label">{name}</span>
        </button>
      ))}
    </div>
  )
}

export default function GianmunPage() {
  const [templates, setTemplates] = useState([])
  const [form, setForm] = useState({ template: '', subject: '', body_instruction: '', model: null, output_path: '' })
  const [preview, setPreview] = useState('')
  const [thinking, setThinking] = useState('')
  const [fetchingUrls, setFetchingUrls] = useState([])
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [validation, setValidation] = useState(null)
  const [validating, setValidating] = useState(false)
  const toast = useToast()
  const bodyRef = useRef(null)

  useEffect(() => {
    fetchJSON(API.gianmunTemplates).then(d => {
      if (d?.templates) setTemplates(d.templates)
    }).catch(() => {})
  }, [])

  function updateField(key, val) {
    setForm(f => ({ ...f, [key]: val }))
  }

  async function handleAiGenerate() {
    if (!form.subject) { toast('제목을 입력하세요', 'warning'); return }
    setGenerating(true)
    setPreview('')
    setThinking('')
    setFetchingUrls([])
    setValidation(null)

    let fullText = ''
    try {
      const res = await fetch(API.gianmunAiBody, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_type: form.template || '일반기안',
          subject: form.subject,
          instruction: form.body_instruction,
          model: form.model,
        }),
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const ev = JSON.parse(line.slice(6))
              if (ev.type === 'token') {
                fullText += ev.content
                setPreview(p => p + ev.content)
              }
              else if (ev.type === 'thinking') setThinking(t => t + ev.content)
              else if (ev.type === 'fetching') setFetchingUrls(prev => [...prev, ev.status || ev.url])
              else if (ev.type === 'error') toast(ev.message, 'error')
            } catch {}
          }
        }
      }
    } catch {
      toast('AI 생성 실패', 'error')
    } finally {
      setGenerating(false)
    }

    // 스트리밍 완료 후 자동 검증
    if (fullText) {
      setValidating(true)
      try {
        const v = await postJSON(API.gianmunValidate, { text: fullText })
        setValidation(v)
      } catch { /* 검증 실패는 무시 */ }
      finally { setValidating(false) }
    }
  }

  async function handleSave() {
    if (!form.template || !form.subject) { toast('템플릿과 제목을 입력하세요', 'warning'); return }
    setSaving(true)
    try {
      const payload = {
        doc_type: form.template || '일반기안',
        subject: form.subject,
        body: preview || form.body_instruction,
      }
      if (form.output_path.trim()) payload.output_path = form.output_path.trim()
      const result = await postJSON(API.gianmunSave, payload)
      toast(`저장 완료: ${result?.path || ''}`, 'success')
    } catch {
      toast('저장 실패', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-gianmun">
      <h2>기안문 작성</h2>

      <div className="split-view">
        <div className="split-left">
          <div className="form-group">
            <label>템플릿 유형</label>
            <TemplateCards
              templates={templates.length > 0 ? templates.map(t => t.name) : FALLBACK_TEMPLATES}
              value={form.template}
              onChange={v => updateField('template', v)}
            />
          </div>

          <div className="form-group">
            <label>제목</label>
            <input
              type="text"
              value={form.subject}
              onChange={e => updateField('subject', e.target.value)}
              placeholder="예: 2026년도 AI 도서관 도슨트 양성 계획"
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>본문 지시사항 (선택)</span>
              <span className={`char-counter ${form.body_instruction.length >= 500 ? 'char-counter-red' : form.body_instruction.length >= 400 ? 'char-counter-amber' : ''}`}>
                {form.body_instruction.length}/500
              </span>
            </label>
            <textarea
              ref={bodyRef}
              rows={6}
              value={form.body_instruction}
              onChange={e => updateField('body_instruction', e.target.value.slice(0, 500))}
              placeholder="AI에게 본문 작성 방향을 알려주세요..."
            />
          </div>

          <div className="form-group">
            <label>AI 모델</label>
            <ModelSelector value={form.model} onChange={v => updateField('model', v)} task="gianmun_body" />
          </div>

          <div className="form-group">
            <label>저장 경로 (선택)</label>
            <div className="save-path-row">
              <div className={`save-path-display${form.output_path ? '' : ' empty'}`}>
                {form.output_path || '기본 경로 (문서 폴더)'}
              </div>
              {form.output_path && (
                <button className="save-path-clear" onClick={() => updateField('output_path', '')} title="초기화">&times;</button>
              )}
              <button className="btn btn-browse" onClick={() => setPickerOpen(true)}>찾아보기</button>
            </div>
          </div>

          <div className="form-actions">
            <button className="btn btn-primary" onClick={handleAiGenerate} disabled={generating}>
              {generating ? 'AI 생성 중...' : 'AI 본문 생성'}
            </button>
            <button className="btn btn-success" onClick={handleSave} disabled={saving}>
              {saving ? '저장 중...' : 'HWPX 저장'}
            </button>
          </div>
        </div>

        <div className="split-right">
          <ThinkingPanel content={thinking} />
          {fetchingUrls.length > 0 && (
            <div className="fetching-status">
              <strong>참고 웹 페이지:</strong>
              {fetchingUrls.map((s, i) => <div key={i} className="fetching-url">{s}</div>)}
            </div>
          )}
          <GuardSummaryBar
            dateGuard={validation?.date_guard}
            pii={validation?.pii}
            budget={validation?.budget}
            loading={validating}
          />
          <div className="preview-pane">
            <div className="preview-header">미리보기</div>
            {preview ? (
              validation?.annotations?.length > 0 ? (
                <AnnotatedPreview text={preview} annotations={validation.annotations} />
              ) : (
                <div className="preview-body" style={{ whiteSpace: 'pre-wrap' }}>{preview}</div>
              )
            ) : (
              <div className="preview-empty">
                <span style={{ fontSize: 48 }}>{'✍️'}</span>
                <span>AI 생성 버튼을 클릭하면 미리보기가 표시됩니다</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <FolderPicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={path => updateField('output_path', path)}
        mode="save"
        defaultName={form.subject ? `${form.subject}.hwpx` : '기안문.hwpx'}
      />
    </div>
  )
}
