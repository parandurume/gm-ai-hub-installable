import { useState, useRef, useEffect, useCallback } from 'react'
import { fetchJSON, postJSON, API, aiErrorMessage } from '../utils/api'
import FolderPicker from '../components/FolderPicker'
import ModelSelector from '../components/ModelSelector'
import ThinkingPanel from '../components/ThinkingPanel'
import { useToast } from '../hooks/useToast'
import { useAiBusy } from '../hooks/useAiBusy'

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

  const [streamingSummary, setStreamingSummary] = useState('')
  const [streamingThinking, setStreamingThinking] = useState('')
  const [sttCached, setSttCached] = useState(null)
  const [sttAvailable, setSttAvailable] = useState(null)
  const [sttModelPath, setSttModelPath] = useState('')
  const [sttPathInput, setSttPathInput] = useState('')
  const [sttPathSaving, setSttPathSaving] = useState(false)
  const [showSttPathForm, setShowSttPathForm] = useState(false)
  const [savePath, setSavePath] = useState('')
  const [savePickerOpen, setSavePickerOpen] = useState(false)
  const [showSaveOptions, setShowSaveOptions] = useState(false)
  const [saving, setSaving] = useState(false)
  const [resavePickerOpen, setResavePickerOpen] = useState(false)

  const mediaRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const fileInputRef = useRef(null)
  const toast = useToast()
  const { setBusy, clearBusy } = useAiBusy()

  useEffect(() => {
    fetchJSON(API.meetingSttStatus)
      .then(d => {
        setSttAvailable(d.available !== false)
        setSttCached(d.cached)
        if (d.model_path) {
          setSttModelPath(d.model_path)
          setSttPathInput(d.model_path)
        }
      })
      .catch(() => {
        setSttAvailable(null)
        setSttCached(null)
      })
    fetchJSON(API.settings)
      .then(s => { if (s.meeting_save_dir) setSavePath(s.meeting_save_dir) })
      .catch(() => {})
  }, [])

  function updateField(key, val) {
    setForm(f => ({ ...f, [key]: val }))
  }

  // ── STT 수동 모델 경로 ───────────────────────────────────────
  async function handleSttPathSave() {
    setSttPathSaving(true)
    try {
      const res = await postJSON(API.meetingSttModelPath, { path: sttPathInput.trim() })
      setSttModelPath(res.path || '')
      setSttCached(res.cached)
      setShowSttPathForm(false)
      toast(res.path ? '모델 경로가 설정되었습니다' : '자동 다운로드 모드로 전환되었습니다', 'success')
    } catch (err) {
      toast(err.message || '경로 설정 실패', 'error')
    } finally {
      setSttPathSaving(false)
    }
  }

  async function handleSttPathClear() {
    setSttPathSaving(true)
    try {
      await postJSON(API.meetingSttModelPath, { path: '' })
      setSttModelPath('')
      setSttPathInput('')
      // 상태 다시 확인
      const d = await fetchJSON(API.meetingSttStatus)
      setSttCached(d.cached)
      toast('모델 경로 초기화 (자동 다운로드 모드)', 'success')
    } catch (err) {
      toast(err.message || '초기화 실패', 'error')
    } finally {
      setSttPathSaving(false)
    }
  }

  // ── Recording ──────────────────────────────────────────────────

  async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      toast('이 브라우저에서 마이크를 사용할 수 없습니다. HTTPS 또는 localhost로 접속하세요.', 'error')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // mimeType 지원 여부 확인 후 fallback
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm'
        : MediaRecorder.isTypeSupported('audio/ogg') ? 'audio/ogg'
        : ''
      const mr = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
      const usedMime = mr.mimeType || 'audio/webm'
      chunksRef.current = []
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        handleTranscribe(new Blob(chunksRef.current, { type: usedMime }))
      }
      mediaRef.current = mr
      mr.start(500)
      setRecording(true)
      setRecordSec(0)
      timerRef.current = setInterval(() => setRecordSec(s => s + 1), 1000)
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        toast('마이크 접근 권한이 필요합니다. 브라우저 설정에서 마이크를 허용하세요.', 'error')
      } else if (err.name === 'NotFoundError') {
        toast('마이크 장치를 찾을 수 없습니다. 마이크가 연결되어 있는지 확인하세요.', 'error')
      } else if (err.name === 'NotReadableError') {
        toast('마이크가 다른 프로그램에서 사용 중입니다.', 'error')
      } else {
        toast(`녹음 시작 실패: ${err.name || '알 수 없는 오류'} — ${err.message}`, 'error')
      }
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
      const ext = (blob.type || '').includes('ogg') ? '.ogg' : (blob.type || '').includes('mp4') ? '.m4a' : '.webm'
      fd.append('file', blob, `recording${ext}`)
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
        // Auto PII scan on transcription result
        try {
          const pii = await postJSON(API.piiScanText, { text: data.text })
          if (!pii.passed) {
            toast(`주의: 음성 인식 결과에서 개인정보 ${pii.total_found}건 감지됨`, 'warning')
          }
        } catch { /* PII scan failure is non-critical */ }
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
    setBusy('회의록 생성 중...')
    setResult(null)
    setStreamingSummary('')
    setStreamingThinking('')

    let fullSummary = ''
    let fullThinking = ''
    let resultPath = ''

    try {
      const res = await fetch(API.meetingStream, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: form.title,
          date: form.date,
          attendees: form.attendees,
          content: form.content,
          location: form.location,
          decisions: form.decisions,
          action_items: form.action_items,
          model: form.model,
          output_path: savePath || undefined,
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
              if (ev.type === 'token') {
                fullSummary += ev.content
                setStreamingSummary(s => s + ev.content)
              } else if (ev.type === 'thinking') {
                fullThinking += ev.content
                setStreamingThinking(t => t + ev.content)
              } else if (ev.type === 'done') {
                resultPath = ev.path || ''
              } else if (ev.type === 'error') {
                toast(ev.message, 'error')
              }
            } catch {}
          }
        }
      }

      setResult({
        summary: fullSummary || form.content,
        thinking: fullThinking || null,
        path: resultPath,
      })
      toast('회의록 생성 완료', 'success')
    } catch (err) {
      toast(aiErrorMessage('회의록 생성', err), 'error')
    } finally {
      setLoading(false)
      clearBusy()
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

  async function handleSaveHwpx(outputPath) {
    if (!result?.summary) return
    setSaving(true)
    try {
      const res = await postJSON(API.meetingSave, {
        title: form.title,
        date: form.date,
        attendees: form.attendees,
        content: result.summary,
        location: form.location,
        decisions: form.decisions,
        action_items: form.action_items,
        output_path: outputPath || savePath || undefined,
      })
      if (res.path) {
        setResult(prev => ({ ...prev, path: res.path }))
        toast(`HWPX 저장 완료: ${res.path}`, 'success')
      }
    } catch (err) {
      toast(aiErrorMessage('HWPX 저장', err), 'error')
    } finally {
      setSaving(false)
    }
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
                    <div>⚠ 음성 인식 모듈(faster-whisper)이 설치되지 않았습니다</div>
                    <div className="stt-install-actions">
                      <button className="btn btn-primary btn-sm" onClick={() => setShowSttPathForm(v => !v)}>
                        설치 방법 보기
                      </button>
                    </div>
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
                    {sttCached === false && !sttModelPath && (
                      <span className="stt-cache-notice">
                        ⚠ 첫 사용 시 ~1.5 GB 다운로드{' '}
                        <button className="btn-link" onClick={() => setShowSttPathForm(v => !v)}>
                          수동 경로 설정
                        </button>
                      </span>
                    )}
                    {sttModelPath && (
                      <span className="stt-cache-notice stt-manual-path-active">
                        수동 모델: {sttModelPath.split(/[/\\]/).pop()}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* STT 수동 모델 경로 설정 폼 */}
              {showSttPathForm && (
                <div className="stt-path-form">
                  <div className="stt-path-form-header">
                    <strong>음성 인식(STT) 설치 안내</strong>
                    <button className="btn btn-icon btn-danger-ghost" onClick={() => setShowSttPathForm(false)}>&times;</button>
                  </div>

                  {sttDisabled && (
                    <div className="stt-install-guide">
                      <div className="stt-install-step">
                        <span className="stt-step-num">1</span>
                        <div>
                          <strong>Python 패키지 설치</strong> (관리자 권한 명령 프롬프트)
                          <code className="stt-code-block">pip install faster-whisper av</code>
                        </div>
                      </div>
                      <div className="stt-install-step">
                        <span className="stt-step-num">2</span>
                        <div>
                          <strong>앱 재시작</strong> — 설치 후 GM-AI-Hub를 종료하고 다시 실행하세요.
                        </div>
                      </div>
                      <div className="stt-install-divider">
                        <span>또는 모델을 직접 다운로드</span>
                      </div>
                      <div className="stt-install-step">
                        <span className="stt-step-num">A</span>
                        <div>
                          <strong>모델 다운로드</strong> (~1.5 GB)
                          <br />
                          <a
                            href="https://huggingface.co/Systran/faster-whisper-medium/tree/main"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="stt-download-link"
                          >
                            Hugging Face에서 faster-whisper-medium 다운로드 &rarr;
                          </a>
                          <div className="stt-help-detail">
                            위 링크에서 모든 파일을 하나의 폴더에 다운로드하세요.
                            <br />
                            필수 파일: <code>model.bin</code>, <code>config.json</code>, <code>vocabulary.json</code> 등
                          </div>
                        </div>
                      </div>
                      <div className="stt-install-step">
                        <span className="stt-step-num">B</span>
                        <div>
                          <strong>아래에 모델 폴더 경로를 입력하세요</strong>
                        </div>
                      </div>
                    </div>
                  )}

                  {!sttDisabled && (
                    <p className="stt-path-help">
                      자동 다운로드가 안 되는 경우, faster-whisper 모델 폴더를 직접 지정하세요.<br />
                      모델 폴더 안에 <code>model.bin</code> 파일이 있어야 합니다.
                    </p>
                  )}

                  <div className="stt-path-input-row">
                    <input
                      type="text"
                      value={sttPathInput}
                      onChange={e => setSttPathInput(e.target.value)}
                      placeholder="예: C:\models\faster-whisper-medium"
                    />
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={handleSttPathSave}
                      disabled={sttPathSaving || !sttPathInput.trim()}
                    >
                      {sttPathSaving ? '확인 중...' : '적용'}
                    </button>
                    {sttModelPath && (
                      <button className="btn btn-secondary btn-sm" onClick={handleSttPathClear} disabled={sttPathSaving}>
                        초기화
                      </button>
                    )}
                  </div>
                </div>
              )}

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

            {/* ── 저장 위치 ── */}
            <div className="meeting-details-section">
              <button
                type="button"
                className="meeting-details-toggle"
                onClick={() => setShowSaveOptions(v => !v)}
              >
                <span>{showSaveOptions ? '\u25BE' : '\u25B8'} 저장 위치</span>
                <span className="meeting-details-hint">
                  {savePath || '기본 (작업 폴더)'}
                </span>
              </button>
              {showSaveOptions && (
                <div className="meeting-details-body">
                  <div className="save-path-row">
                    <div className={`save-path-display${savePath ? '' : ' empty'}`}>
                      {savePath || '기본 경로 (작업 폴더)'}
                    </div>
                    {savePath && (
                      <button className="save-path-clear" onClick={() => setSavePath('')} title="초기화">&times;</button>
                    )}
                    <button className="btn btn-browse" onClick={() => setSavePickerOpen(true)}>찾아보기</button>
                  </div>
                </div>
              )}
            </div>
            <FolderPicker
              open={savePickerOpen}
              onClose={() => setSavePickerOpen(false)}
              onSelect={path => { setSavePath(path); setSavePickerOpen(false) }}
              mode="folder"
            />
            <FolderPicker
              open={resavePickerOpen}
              onClose={() => setResavePickerOpen(false)}
              onSelect={path => { setResavePickerOpen(false); handleSaveHwpx(path) }}
              mode="folder"
            />

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
          {(loading || result) ? (
            <>
              <div className="panel-header">
                <span>{loading ? 'AI 회의록 생성 중...' : 'AI 회의록'}</span>
                {!loading && result && (
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
                )}
                {loading && <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />}
              </div>
              {result?.path && (
                <div className="meeting-result-path">
                  💾 {result.path}
                </div>
              )}
              <div className="panel-body" style={{ flex: 1, overflowY: 'auto' }}>
                <ThinkingPanel content={result?.thinking || streamingThinking} />
                <div className="meeting-result-text">
                  {result?.summary || streamingSummary || (
                    <div className="skeleton-loader">
                      <div className="skeleton-line" />
                      <div className="skeleton-line" />
                      <div className="skeleton-line" />
                    </div>
                  )}
                </div>
              </div>
              {!loading && result && (
                <div className="meeting-result-actions">
                  <button
                    className="btn btn-success"
                    onClick={() => handleSaveHwpx()}
                    disabled={saving}
                  >
                    {saving ? '저장 중...' : 'HWPX 저장'}
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setResavePickerOpen(true)}
                    disabled={saving}
                  >
                    다른 위치에 저장
                  </button>
                </div>
              )}
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
