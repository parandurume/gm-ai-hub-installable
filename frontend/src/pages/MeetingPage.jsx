import { useState, useRef, useEffect, useCallback } from 'react'
import { postJSON, fetchJSON, API } from '../utils/api'
import ModelSelector from '../components/ModelSelector'
import ThinkingPanel from '../components/ThinkingPanel'
import { useToast } from '../hooks/useToast'

/** Pill-style tag input for attendees. Syncs to a comma-separated string. */
function AttendeesTagInput({ value, onChange }) {
  const tags = value ? value.split(',').map(s => s.trim()).filter(Boolean) : []
  const [inputVal, setInputVal] = useState('')
  const inputRef = useRef(null)

  const addTag = useCallback((raw) => {
    const name = raw.trim()
    if (!name || tags.includes(name)) { setInputVal(''); return }
    onChange([...tags, name].join(', '))
    setInputVal('')
  }, [tags, onChange])

  function removeTag(idx) {
    const next = tags.filter((_, i) => i !== idx)
    onChange(next.join(', '))
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTag(inputVal)
    } else if (e.key === 'Backspace' && !inputVal && tags.length > 0) {
      removeTag(tags.length - 1)
    }
  }

  function handleBlur() {
    if (inputVal.trim()) addTag(inputVal)
  }

  return (
    <div className="attendees-tag-input" onClick={() => inputRef.current?.focus()}>
      {tags.map((tag, i) => (
        <span key={i} className="attendee-tag">
          {tag}
          <button type="button" className="attendee-tag-remove" onClick={() => removeTag(i)} aria-label={`${tag} 제거`}>×</button>
        </span>
      ))}
      <input
        ref={inputRef}
        value={inputVal}
        onChange={e => setInputVal(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={tags.length === 0 ? '이름 입력 후 Enter 또는 쉼표' : ''}
        className="attendees-tag-field"
      />
    </div>
  )
}

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
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [recordSec, setRecordSec] = useState(0)

  const [sttCached, setSttCached] = useState(null) // null=unknown, true/false

  const mediaRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const fileInputRef = useRef(null)
  const toast = useToast()

  // Check model cache status once on mount
  useEffect(() => {
    fetchJSON(API.meetingSttStatus)
      .then(d => setSttCached(d.cached))
      .catch(() => setSttCached(null))
  }, [])

  function updateField(key, val) {
    setForm(f => ({ ...f, [key]: val }))
  }

  // Show a one-time warning if the model hasn't been downloaded yet.
  // Returns true if the user wants to proceed, false to abort.
  async function confirmIfNotCached() {
    if (sttCached) return true
    return window.confirm(
      '음성 인식 모델(약 1.5 GB)이 아직 설치되어 있지 않습니다.\n' +
      '첫 번째 사용 시 인터넷에서 자동으로 다운로드됩니다.\n\n' +
      '인터넷 연결을 확인하고 계속하시겠습니까?\n' +
      '(다운로드 중에는 "음성 인식 중..." 메시지가 표시됩니다.)'
    )
  }

  // ── Recording ───────────────────────────────────────────────

  async function startRecording() {
    if (!await confirmIfNotCached()) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      chunksRef.current = []
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        handleTranscribe(new Blob(chunksRef.current, { type: 'audio/webm' }))
      }
      mediaRef.current = mr
      mr.start(500) // collect every 500ms for reliability
      setRecording(true)
      setRecordSec(0)
      timerRef.current = setInterval(() => setRecordSec(s => s + 1), 1000)
    } catch {
      toast('마이크 접근 권한이 필요합니다', 'error')
    }
  }

  function stopRecording() {
    clearInterval(timerRef.current)
    mediaRef.current?.stop()
    setRecording(false)
  }

  async function handleTranscribe(blob) {
    setTranscribing(true)
    try {
      const fd = new FormData()
      fd.append('file', blob, 'recording.webm')
      const res = await fetch(API.meetingTranscribe, { method: 'POST', body: fd })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      if (data.text) {
        updateField('content', form.content ? form.content + '\n' + data.text : data.text)
        setSttCached(true) // model is now cached — skip warning on future uses
        toast('음성 인식 완료', 'success')
      }
    } catch (e) {
      toast(`음성 인식 실패: ${e.message}`, 'error')
    } finally {
      setTranscribing(false)
    }
  }

  async function handleAudioFile(e) {
    const file = e.target.files[0]
    if (!file) return
    e.target.value = ''
    if (!await confirmIfNotCached()) return
    handleTranscribe(file)
  }

  // ── Meeting generation ──────────────────────────────────────

  async function handleGenerate() {
    if (!form.content.trim()) { toast('회의 내용을 입력하세요', 'warning'); return }
    setLoading(true)
    try {
      const data = await postJSON(API.meeting, {
        title: form.title,
        date: form.date,           // backend alias: meeting_date
        attendees: form.attendees, // comma-separated string
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

  const busy = recording || transcribing || loading

  return (
    <div className="page-meeting">
      <h2>회의록 작성</h2>

      <div className="split-view">
        {/* ── 입력 패널 ── */}
        <div className="panel" style={{ padding: 20, overflowY: 'auto' }}>
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
              <input
                type="date"
                value={form.date}
                onChange={e => updateField('date', e.target.value)}
              />
            </div>
            <div className="form-group" style={{ flex: 2 }}>
              <label>참석자</label>
              <AttendeesTagInput
                value={form.attendees}
                onChange={v => updateField('attendees', v)}
              />
            </div>
          </div>

          {/* STT controls + textarea */}
          <div className="form-group">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <label style={{ margin: 0 }}>회의 내용 / 메모</label>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {transcribing ? (
                  <span style={{ fontSize: '0.8rem', color: 'var(--teal)' }}>음성 인식 중...</span>
                ) : recording ? (
                  <>
                    <span style={{ fontSize: '0.8rem', color: '#dc2626', fontVariantNumeric: 'tabular-nums' }}>
                      &#9679; {String(Math.floor(recordSec / 60)).padStart(2, '0')}:{String(recordSec % 60).padStart(2, '0')}
                    </span>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '2px 10px', fontSize: '0.8rem' }}
                      onClick={stopRecording}
                    >
                      중지
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '2px 10px', fontSize: '0.8rem' }}
                      onClick={startRecording}
                      disabled={busy}
                      title="마이크로 녹음 후 자동 변환"
                    >
                      &#127908; 녹음
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '2px 10px', fontSize: '0.8rem' }}
                      onClick={() => fileInputRef.current?.click()}
                      disabled={busy}
                      title="오디오 파일 업로드 (mp3 / wav / m4a / webm)"
                    >
                      &#128193; 파일
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="audio/*"
                      style={{ display: 'none' }}
                      onChange={handleAudioFile}
                    />
                  </>
                )}
              </div>
            </div>
            <textarea
              rows={10}
              value={form.content}
              onChange={e => updateField('content', e.target.value)}
              placeholder="회의 중 논의된 내용을 자유롭게 입력하거나, 녹음 버튼으로 음성을 텍스트로 변환하세요..."
              disabled={transcribing}
            />
          </div>

          <div className="form-group">
            <label>AI 모델</label>
            <ModelSelector value={form.model} onChange={v => updateField('model', v)} task="meeting_minutes" />
          </div>

          <button className="btn btn-primary" onClick={handleGenerate} disabled={busy}>
            {loading ? 'AI 요약 중...' : 'AI 회의록 생성'}
          </button>
        </div>

        {/* ── 결과 패널 ── */}
        <div className="panel" style={{ padding: 20, overflowY: 'auto' }}>
          {result?.thinking && <ThinkingPanel content={result.thinking} />}
          {result ? (
            <div className="preview-pane">
              <div className="preview-header">
                AI 회의록
                {result.path && (
                  <span style={{ fontSize: '0.8rem', color: 'var(--ink3)', marginLeft: 8 }}>
                    {result.path}
                  </span>
                )}
              </div>
              <div className="preview-body" style={{ whiteSpace: 'pre-wrap' }}>
                {result.summary}
              </div>
            </div>
          ) : (
            <div className="preview-empty">
              <span style={{ fontSize: 48 }}>&#128203;</span>
              <span>회의 내용을 입력하거나 녹음 후 AI 생성 버튼을 클릭하세요</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
