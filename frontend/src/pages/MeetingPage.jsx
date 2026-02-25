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
    location: '',
    attendees: '',
    content: '',
    decisions: '',
    action_items: '',
    model: null,
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [recordSec, setRecordSec] = useState(0)
  const [showDetails, setShowDetails] = useState(false)
  const [copied, setCopied] = useState(false)
  const [pathCopied, setPathCopied] = useState(false)

  const [sttCached, setSttCached] = useState(null)
  const [sttAvailable, setSttAvailable] = useState(null)

  const mediaRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const fileInputRef = useRef(null)
  const toast = useToast()

  useEffect(() => {
    fetchJSON(API.meetingSttStatus)
      .then(d => {
        setSttAvailable(d.available !== false)
        setSttCached(d.cached)
      })
      .catch(() => {
        setSttAvailable(null)
        setSttCached(null)
      })
  }, [])

  function updateField(key, val) {
    setForm(f => ({ ...f, [key]: val }))
  }

  // ── Recording ──────────────────────────────────────────────────

  async function startRecording() {
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
      mr.start(500)
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
        setSttCached(true)
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
    handleTranscribe(file)
  }

  // ── Meeting generation ─────────────────────────────────────────

  async function handleGenerate() {
    if (!form.content.trim()) { toast('회의 내용을 입력하세요', 'warning'); return }
    setLoading(true)
    try {
      const data = await postJSON(API.meeting, {
        title: form.title,
        date: form.date,
        attendees: form.attendees,
        content: form.content,
        location: form.location,
        decisions: form.decisions,
        action_items: form.action_items,
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

  async function handleCopy() {
    if (!result?.summary) return
    await navigator.clipboard.writeText(result.summary)
    setCopied(true)
    toast('텍스트 복사 완료', 'success')
    setTimeout(() => setCopied(false), 2000)
  }

  async function handleCopyPath() {
    if (!result?.path) return
    await navigator.clipboard.writeText(result.path)
    setPathCopied(true)
    setTimeout(() => setPathCopied(false), 2000)
  }

  const busy = recording || transcribing || loading
  const sttDisabled = sttAvailable === false

  return (
    <div className="page-meeting">
      <div className="split-view">

        {/* ── 왼쪽: 입력 패널 ── */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div className="panel-header">
            <span>📝 회의록 작성</span>
          </div>
          <div className="panel-body" style={{ flex: 1, overflowY: 'auto' }}>

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
              <div className="form-group" style={{ flex: 1 }}>
                <label>장소</label>
                <input
                  type="text"
                  value={form.location}
                  onChange={e => updateField('location', e.target.value)}
                  placeholder="예: 3층 소회의실"
                />
              </div>
            </div>

            <div className="form-group">
              <label>참석자</label>
              <AttendeesTagInput
                value={form.attendees}
                onChange={v => updateField('attendees', v)}
              />
            </div>

            {/* ── 회의 내용 + STT ── */}
            <div className="form-group">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <label style={{ margin: 0 }}>회의 내용 / 메모</label>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  {form.content && !recording && !transcribing && (
                    <button
                      type="button"
                      className="meeting-reset-btn"
                      onClick={() => updateField('content', '')}
                      title="내용 초기화"
                    >
                      ✕ 초기화
                    </button>
                  )}
                </div>
              </div>

              {/* STT controls */}
              <div className="stt-bar">
                {sttDisabled ? (
                  <div className="stt-unavailable-banner">
                    ⚠ 음성 인식 모듈 없음 — 앱을 재설치하세요
                  </div>
                ) : transcribing ? (
                  <span className="stt-status-label">
                    <span className="spinner" style={{ width: 13, height: 13, borderWidth: 2 }} />
                    음성 인식 중...
                  </span>
                ) : recording ? (
                  <div className="stt-recording-active">
                    <span className="stt-rec-dot">●</span>
                    <span className="stt-timer">
                      {String(Math.floor(recordSec / 60)).padStart(2, '0')}:{String(recordSec % 60).padStart(2, '0')}
                    </span>
                    <button className="btn btn-danger btn-sm" onClick={stopRecording}>
                      ■ 중지
                    </button>
                  </div>
                ) : (
                  <div className="stt-buttons">
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={startRecording}
                      disabled={busy}
                      title="마이크로 녹음 후 자동 변환"
                    >
                      🎤 녹음
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={busy}
                      title="오디오 파일 업로드 (mp3 / wav / m4a / webm)"
                    >
                      📁 파일
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="audio/*"
                      style={{ display: 'none' }}
                      onChange={handleAudioFile}
                    />
                    {sttCached === false && (
                      <span className="stt-cache-notice">
                        ⚠ 첫 사용 시 ~1.5 GB 다운로드
                      </span>
                    )}
                  </div>
                )}
              </div>

              <textarea
                rows={9}
                value={form.content}
                onChange={e => updateField('content', e.target.value)}
                placeholder="회의 중 논의된 내용을 자유롭게 입력하거나, 녹음 버튼으로 음성을 텍스트로 변환하세요..."
                disabled={transcribing}
              />
            </div>

            {/* ── 추가 정보 (결정사항, 후속조치) ── */}
            <div className="meeting-details-section">
              <button
                type="button"
                className="meeting-details-toggle"
                onClick={() => setShowDetails(v => !v)}
              >
                <span>{showDetails ? '▾' : '▸'} 추가 정보</span>
                <span className="meeting-details-hint">결정사항, 후속조치</span>
              </button>
              {showDetails && (
                <div className="meeting-details-body">
                  <div className="form-group">
                    <label>결정사항</label>
                    <textarea
                      rows={3}
                      value={form.decisions}
                      onChange={e => updateField('decisions', e.target.value)}
                      placeholder="회의에서 결정된 사항을 입력하세요"
                    />
                  </div>
                  <div className="form-group">
                    <label>후속조치</label>
                    <textarea
                      rows={3}
                      value={form.action_items}
                      onChange={e => updateField('action_items', e.target.value)}
                      placeholder="담당자 및 기한 포함 후속조치를 입력하세요"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="form-group">
              <label>AI 모델</label>
              <ModelSelector value={form.model} onChange={v => updateField('model', v)} task="meeting_minutes" />
            </div>

            <button
              className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={handleGenerate}
              disabled={busy}
            >
              {loading
                ? <><span className="spinner" style={{ width: 13, height: 13, borderWidth: 2 }} /> AI 요약 중...</>
                : 'AI 회의록 생성 ▶'}
            </button>
          </div>
        </div>

        {/* ── 오른쪽: 결과 / 가이드 패널 ── */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {result ? (
            <>
              <div className="panel-header">
                <span>AI 회의록</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button className="btn btn-secondary btn-sm" onClick={handleCopy}>
                    {copied ? '✓ 복사됨' : '복사'}
                  </button>
                  {result.path && (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={handleCopyPath}
                      title={result.path}
                    >
                      {pathCopied ? '✓ 경로 복사됨' : '경로 복사'}
                    </button>
                  )}
                </div>
              </div>
              {result.path && (
                <div className="meeting-result-path">
                  💾 {result.path}
                </div>
              )}
              <div className="panel-body" style={{ flex: 1, overflowY: 'auto' }}>
                {result.thinking && <ThinkingPanel content={result.thinking} />}
                <div className="meeting-result-text">
                  {result.summary}
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="panel-header">
                <span>📋 작성 가이드</span>
              </div>
              <div className="panel-body" style={{ flex: 1, overflowY: 'auto' }}>
                <div className="meeting-guide">
                  <div className="meeting-guide-step">
                    <div className="guide-step-num">1</div>
                    <div className="guide-step-body">
                      <div className="guide-step-title">기본 정보 입력</div>
                      <div className="guide-step-desc">회의 제목, 일자, 장소, 참석자를 입력하세요.</div>
                    </div>
                  </div>
                  <div className="meeting-guide-step">
                    <div className="guide-step-num">2</div>
                    <div className="guide-step-body">
                      <div className="guide-step-title">회의 내용 기록</div>
                      <div className="guide-step-desc">
                        메모를 직접 입력하거나 🎤 <strong>녹음</strong> 버튼으로 음성을 텍스트로 자동 변환하세요.
                        오디오 파일(mp3/wav/m4a)도 📁 <strong>파일</strong> 버튼으로 업로드할 수 있습니다.
                      </div>
                    </div>
                  </div>
                  <div className="meeting-guide-step">
                    <div className="guide-step-num">3</div>
                    <div className="guide-step-body">
                      <div className="guide-step-title">AI 회의록 생성</div>
                      <div className="guide-step-desc">
                        내용이 100자 이상이면 AI가 공문서 형식으로 자동 정리합니다.
                        결정사항·후속조치는 <strong>추가 정보</strong>에서 입력할 수 있습니다.
                      </div>
                    </div>
                  </div>
                  <div className="meeting-guide-step">
                    <div className="guide-step-num">4</div>
                    <div className="guide-step-body">
                      <div className="guide-step-title">HWPX 파일 저장</div>
                      <div className="guide-step-desc">
                        한글(HWP) 문서로 작업 폴더에 자동 저장됩니다.
                        생성 후 <strong>경로 복사</strong> 버튼으로 저장 위치를 확인하세요.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

      </div>
    </div>
  )
}
