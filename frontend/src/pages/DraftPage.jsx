import { useState, useEffect, useRef } from 'react'
import { fetchJSON, postJSON, API, aiErrorMessage } from '../utils/api'
import ModelSelector from '../components/ModelSelector'
import ThinkingPanel from '../components/ThinkingPanel'
import FolderPicker from '../components/FolderPicker'
import GuardSummaryBar from '../components/GuardSummaryBar'
import AnnotatedPreview from '../components/AnnotatedPreview'
import { useToast } from '../hooks/useToast'
import { useAiBusy } from '../hooks/useAiBusy'

const FALLBACK_TEMPLATES = ['일반기안', '협조전', '보고서', '계획서', '결과보고서', '회의록', '민원답변']

const TEMPLATE_ICONS = {
  '일반기안': '📄', '협조전': '🤝', '보고서': '📊',
  '계획서': '📝', '결과보고서': '✅', '회의록': '📋', '민원답변': '📨',
}

const DOC_TYPES = [
  { key: 'draft', label: '기안문', icon: '📄' },
  { key: 'task_order', label: '과업지시서', icon: '📑' },
]

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

/* ── 과업지시서 — 과업범위 동적 항목 ───────────────────── */
function ScopeItems({ items, onChange }) {
  function update(idx, val) {
    const next = [...items]
    next[idx] = val
    onChange(next)
  }
  function remove(idx) {
    onChange(items.filter((_, i) => i !== idx))
  }
  function add() {
    onChange([...items, ''])
  }
  return (
    <div className="scope-items">
      {items.map((item, i) => (
        <div key={i} className="scope-item-row">
          <span className="scope-item-label">{'가나다라마바사아자차카타파하'[i] || String.fromCharCode(0xAC00 + i)}.</span>
          <input
            type="text"
            value={item}
            onChange={e => update(i, e.target.value)}
            placeholder={`과업범위 항목 ${i + 1}`}
          />
          <button type="button" className="btn btn-icon btn-danger-ghost" onClick={() => remove(i)} title="삭제">&times;</button>
        </div>
      ))}
      <button type="button" className="btn btn-sm btn-secondary" onClick={add}>+ 항목 추가</button>
    </div>
  )
}

/* ── 기안문 좌측 폼 ──────────────────────────────────── */
function DraftForm({ templates, form, updateField, generating, saving, onGenerate, onSave, setPickerOpen, bodyRef }) {
  return (
    <>
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
        <ModelSelector value={form.model} onChange={v => updateField('model', v)} task="draft_body" />
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
        <button className="btn btn-primary" onClick={onGenerate} disabled={generating}>
          {generating ? 'AI 생성 중...' : 'AI 본문 생성'}
        </button>
        <button className="btn btn-success" onClick={onSave} disabled={saving}>
          {saving ? '저장 중...' : 'HWPX 저장'}
        </button>
      </div>
    </>
  )
}

/* ── 과업지시서 좌측 폼 ──────────────────────────────── */
function TaskOrderForm({ form, updateField, generating, saving, onGenerate, onSave, setPickerOpen }) {
  return (
    <>
      <div className="form-group">
        <label>과업명</label>
        <input
          type="text"
          value={form.task_name}
          onChange={e => updateField('task_name', e.target.value)}
          placeholder="예: 2026년 광명시 사회적경제 오픈박스 교육 사업"
        />
      </div>

      <div className="form-group">
        <label>과업목적</label>
        <textarea
          rows={3}
          value={form.purpose}
          onChange={e => updateField('purpose', e.target.value)}
          placeholder="사업의 목적을 간략히 기술하세요..."
        />
      </div>

      <div className="form-row-2col">
        <div className="form-group">
          <label>과업기간</label>
          <input
            type="text"
            value={form.period}
            onChange={e => updateField('period', e.target.value)}
            placeholder="예: 착수일로부터 2026. 12. 31.까지"
          />
        </div>
        <div className="form-group">
          <label>과업장소</label>
          <input
            type="text"
            value={form.location}
            onChange={e => updateField('location', e.target.value)}
            placeholder="예: 광명시 관내"
          />
        </div>
      </div>

      <div className="form-group">
        <label>소요예산</label>
        <input
          type="text"
          value={form.budget}
          onChange={e => updateField('budget', e.target.value)}
          placeholder="예: 금20,000천원"
        />
      </div>

      <div className="form-group">
        <label>과업범위 및 주요내용</label>
        <ScopeItems
          items={form.scope_items}
          onChange={v => updateField('scope_items', v)}
        />
      </div>

      <div className="form-group">
        <label style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>추가 지시사항 (선택)</span>
          <span className={`char-counter ${form.details.length >= 1000 ? 'char-counter-red' : form.details.length >= 800 ? 'char-counter-amber' : ''}`}>
            {form.details.length}/1000
          </span>
        </label>
        <textarea
          rows={4}
          value={form.details}
          onChange={e => updateField('details', e.target.value.slice(0, 1000))}
          placeholder="세부사업 내용, 참여대상, 홍보 방안 등 추가 정보를 입력하세요..."
        />
      </div>

      <div className="form-group">
        <label>AI 모델</label>
        <ModelSelector value={form.model} onChange={v => updateField('model', v)} task="task_order" />
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
        <button className="btn btn-primary" onClick={onGenerate} disabled={generating}>
          {generating ? 'AI 생성 중...' : 'AI 과업지시서 생성'}
        </button>
        <button className="btn btn-success" onClick={onSave} disabled={saving}>
          {saving ? '저장 중...' : 'HWPX 저장'}
        </button>
      </div>
    </>
  )
}

/* ── 메인 페이지 ─────────────────────────────────────── */
export default function DraftPage() {
  const [docType, setDocType] = useState('draft')
  const [templates, setTemplates] = useState([])

  // 기안문 폼 상태
  const [draftForm, setDraftForm] = useState({ template: '', subject: '', body_instruction: '', model: null, output_path: '' })
  // 과업지시서 폼 상태
  const [toForm, setToForm] = useState({
    task_name: '', purpose: '', period: '', location: '', budget: '',
    scope_items: [''], details: '', model: null, output_path: '',
  })

  const [preview, setPreview] = useState('')
  const [thinking, setThinking] = useState('')
  const [fetchingUrls, setFetchingUrls] = useState([])
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [validation, setValidation] = useState(null)
  const [validating, setValidating] = useState(false)
  const [editing, setEditing] = useState(false)
  const toast = useToast()
  const { setBusy, clearBusy } = useAiBusy()
  const bodyRef = useRef(null)

  useEffect(() => {
    fetchJSON(API.draftTemplates).then(d => {
      if (d?.templates) setTemplates(d.templates)
    }).catch(() => {})
  }, [])

  function updateDraftField(key, val) { setDraftForm(f => ({ ...f, [key]: val })) }
  function updateToField(key, val) { setToForm(f => ({ ...f, [key]: val })) }

  // 문서 유형 전환 시 미리보기 초기화
  function switchDocType(key) {
    if (key === docType) return
    setDocType(key)
    setPreview('')
    setThinking('')
    setFetchingUrls([])
    setValidation(null)
    setEditing(false)
  }

  /* ── 기안문 AI 생성 ─────────────────────────────────── */
  async function handleDraftGenerate() {
    if (!draftForm.subject) { toast('제목을 입력하세요', 'warning'); return }
    setGenerating(true)
    setBusy('기안문 생성 중...')
    setPreview('')
    setThinking('')
    setFetchingUrls([])
    setValidation(null)

    let fullText = ''
    try {
      const res = await fetch(API.draftAiBody, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_type: draftForm.template || '일반기안',
          subject: draftForm.subject,
          instruction: draftForm.body_instruction,
          model: draftForm.model,
        }),
      })

      if (!res.ok) {
        let detail = ''
        try { const body = await res.json(); detail = body.detail || '' } catch {}
        throw Object.assign(new Error(detail || `HTTP ${res.status}`), { status: res.status })
      }

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
              if (ev.type === 'token') { fullText += ev.content; setPreview(p => p + ev.content) }
              else if (ev.type === 'thinking') setThinking(t => t + ev.content)
              else if (ev.type === 'fetching') setFetchingUrls(prev => [...prev, ev.status || ev.url])
              else if (ev.type === 'error') toast(ev.message, 'error')
            } catch {}
          }
        }
      }
    } catch (err) {
      toast(aiErrorMessage('AI 본문 생성', err), 'error')
    } finally {
      setGenerating(false)
      clearBusy()
    }

    if (fullText) {
      setValidating(true)
      try { setValidation(await postJSON(API.draftValidate, { text: fullText })) } catch {}
      finally { setValidating(false) }
    }
  }

  async function handleDraftSave() {
    if (!draftForm.template || !draftForm.subject) { toast('템플릿과 제목을 입력하세요', 'warning'); return }
    setSaving(true)
    try {
      const payload = {
        doc_type: draftForm.template || '일반기안',
        subject: draftForm.subject,
        body: preview || draftForm.body_instruction,
      }
      if (draftForm.output_path.trim()) payload.output_path = draftForm.output_path.trim()
      const result = await postJSON(API.draftSave, payload)
      toast(`저장 완료: ${result?.path || ''}`, 'success')
    } catch (err) {
      toast(aiErrorMessage('문서 저장', err), 'error')
    } finally {
      setSaving(false)
    }
  }

  /* ── 과업지시서 AI 생성 ─────────────────────────────── */
  async function handleToGenerate() {
    if (!toForm.task_name) { toast('과업명을 입력하세요', 'warning'); return }
    setGenerating(true)
    setBusy('과업지시서 생성 중...')
    setPreview('')
    setThinking('')
    setValidation(null)

    let fullText = ''
    try {
      const res = await fetch(API.taskOrderGenerate, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_name: toForm.task_name,
          purpose: toForm.purpose,
          period: toForm.period,
          location: toForm.location,
          budget: toForm.budget,
          scope_items: toForm.scope_items.filter(s => s.trim()),
          details: toForm.details,
          model: toForm.model,
        }),
      })

      if (!res.ok) {
        let detail = ''
        try { const body = await res.json(); detail = body.detail || '' } catch {}
        throw Object.assign(new Error(detail || `HTTP ${res.status}`), { status: res.status })
      }

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
              if (ev.type === 'token') { fullText += ev.content; setPreview(p => p + ev.content) }
              else if (ev.type === 'thinking') setThinking(t => t + ev.content)
              else if (ev.type === 'error') toast(ev.message, 'error')
            } catch {}
          }
        }
      }
    } catch (err) {
      toast(aiErrorMessage('과업지시서 생성', err), 'error')
    } finally {
      setGenerating(false)
      clearBusy()
    }

    if (fullText) {
      setValidating(true)
      try { setValidation(await postJSON(API.taskOrderValidate, { text: fullText })) } catch {}
      finally { setValidating(false) }
    }
  }

  async function handleToSave() {
    if (!toForm.task_name) { toast('과업명을 입력하세요', 'warning'); return }
    if (!preview) { toast('먼저 AI 생성을 실행하세요', 'warning'); return }
    setSaving(true)
    try {
      const payload = { task_name: toForm.task_name, body: preview }
      if (toForm.output_path.trim()) payload.output_path = toForm.output_path.trim()
      const result = await postJSON(API.taskOrderSave, payload)
      toast(`저장 완료: ${result?.path || ''}`, 'success')
    } catch (err) {
      toast(aiErrorMessage('과업지시서 저장', err), 'error')
    } finally {
      setSaving(false)
    }
  }

  const validateUrl = docType === 'task_order' ? API.taskOrderValidate : API.draftValidate
  const defaultFileName = docType === 'task_order'
    ? (toForm.task_name ? `${toForm.task_name} 과업지시서.hwpx` : '과업지시서.hwpx')
    : (draftForm.subject ? `${draftForm.subject}.hwpx` : '기안문.hwpx')

  return (
    <div className="page-draft">
      <h2>기안문 작성</h2>

      {/* 문서 유형 탭 */}
      <div className="doc-type-tabs">
        {DOC_TYPES.map(dt => (
          <button
            key={dt.key}
            type="button"
            className={`doc-type-tab ${docType === dt.key ? 'active' : ''}`}
            onClick={() => switchDocType(dt.key)}
          >
            <span className="doc-type-tab-icon">{dt.icon}</span>
            <span>{dt.label}</span>
          </button>
        ))}
      </div>

      <div className="split-view">
        <div className="split-left">
          {docType === 'draft' ? (
            <DraftForm
              templates={templates}
              form={draftForm}
              updateField={updateDraftField}
              generating={generating}
              saving={saving}
              onGenerate={handleDraftGenerate}
              onSave={handleDraftSave}
              setPickerOpen={setPickerOpen}
              bodyRef={bodyRef}
            />
          ) : (
            <TaskOrderForm
              form={toForm}
              updateField={updateToField}
              generating={generating}
              saving={saving}
              onGenerate={handleToGenerate}
              onSave={handleToSave}
              setPickerOpen={setPickerOpen}
            />
          )}
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
            <div className="preview-header">
              <span>미리보기</span>
              {preview && !generating && (
                <button className="btn btn-sm btn-secondary" onClick={() => {
                  if (editing) {
                    setEditing(false)
                    postJSON(validateUrl, { text: preview }).then(setValidation).catch(() => {})
                  } else {
                    setEditing(true)
                    setValidation(null)
                  }
                }}>
                  {editing ? '완료' : '수정'}
                </button>
              )}
            </div>
            {preview ? (
              editing ? (
                <textarea className="preview-edit-textarea" value={preview}
                  onChange={e => setPreview(e.target.value)} />
              ) : validation?.annotations?.length > 0 ? (
                <AnnotatedPreview text={preview} annotations={validation.annotations} />
              ) : (
                <div className="preview-body" style={{ whiteSpace: 'pre-wrap' }}>{preview}</div>
              )
            ) : generating ? (
              <div className="skeleton-loader">
                <div className="skeleton-line" />
                <div className="skeleton-line" />
                <div className="skeleton-line" />
                <div className="skeleton-line" />
              </div>
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
        onSelect={path => {
          if (docType === 'draft') updateDraftField('output_path', path)
          else updateToField('output_path', path)
        }}
        mode="save"
        defaultName={defaultFileName}
      />
    </div>
  )
}
