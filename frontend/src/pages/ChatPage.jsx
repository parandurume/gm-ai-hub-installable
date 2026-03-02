import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { useLocation } from 'react-router-dom'
import { fetchJSON, postJSON, API } from '../utils/api'
import { timeAgo } from '../utils/date'
import { useWebSocket } from '../hooks/useWebSocket'
import ModelSelector from '../components/ModelSelector'
import ThinkingPanel from '../components/ThinkingPanel'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../hooks/useToast'
import { useAiBusy } from '../hooks/useAiBusy'

const REASONING_LABELS = { low: '빠른 답변', medium: '균형', high: '깊은 분석' }
const MAX_INPUT = 2000

const EXAMPLE_PROMPTS = [
  '기안문 초안 작성 방법을 알려줘',
  '회의록 양식 예시를 보여줘',
  '민원 답변서 작성 시 유의사항은?',
  '주요 사업 계획서를 작성해줘',
]

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [model, setModel] = useState(null)
  const [reasoning, setReasoning] = useState('medium')
  const [deepMode, setDeepMode] = useState(false)
  const [clearConfirm, setClearConfirm] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [copiedIdx, setCopiedIdx] = useState(null)
  const [elapsed, setElapsed] = useState(0)
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [pendingImages, setPendingImages] = useState([])
  const [uploading, setUploading] = useState(false)
  const [modelSwitchNotice, setModelSwitchNotice] = useState(null)
  const activeSessionRef = useRef(null)
  const toast = useToast()
  const { setBusy, clearBusy } = useAiBusy()
  const location = useLocation()
  const { text, thinking, fetchedUrls, modelSwitch, isStreaming, sendMessage, stop } = useWebSocket(
    API.chatStream,
    { onError: (msg) => toast(msg, 'error') },
  )
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  const textRef = useRef(text)
  const thinkingRef = useRef(thinking)
  textRef.current = text
  thinkingRef.current = thinking
  activeSessionRef.current = activeSessionId

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, text, thinking])

  useEffect(() => {
    if (!isStreaming && textRef.current) {
      setMessages(m => [...m, { role: 'assistant', content: textRef.current, thinking: thinkingRef.current }])
    }
  }, [isStreaming])

  // Global AI-busy indicator
  useEffect(() => {
    if (isStreaming) setBusy('AI 응답 중...')
    else clearBusy()
  }, [isStreaming, setBusy, clearBusy])

  // Elapsed timer while waiting for first token
  useEffect(() => {
    if (!isStreaming) { setElapsed(0); return }
    const start = Date.now()
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000)
    return () => clearInterval(id)
  }, [isStreaming])

  // Track model auto-switch notice
  useEffect(() => {
    if (modelSwitch) setModelSwitchNotice(modelSwitch)
    if (!isStreaming) setModelSwitchNotice(null)
  }, [modelSwitch, isStreaming])

  // Pre-fill input from location state (e.g. from RegulationPage "AI에게 물어보기")
  useEffect(() => {
    if (location.state?.prefill) {
      setInput(location.state.prefill)
      window.history.replaceState({}, '')
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Load sessions on mount
  const loadSessions = useCallback(() => {
    fetchJSON(API.chatSessions).then(d => setSessions(d?.sessions || [])).catch(() => {})
  }, [])
  useEffect(() => { loadSessions() }, [loadSessions])

  // Auto-save assistant message to session when streaming ends
  const prevStreamingRef = useRef(false)
  useEffect(() => {
    if (prevStreamingRef.current && !isStreaming && textRef.current) {
      const sid = activeSessionRef.current
      if (sid) {
        // Save user message (last user msg) + assistant message
        const lastUserMsg = messages.findLast?.(m => m.role === 'user')
        if (lastUserMsg) {
          postJSON(`${API.chatSessions}/${sid}/messages`, {
            role: 'user', content: lastUserMsg.content,
            images: lastUserMsg.image_ids?.length ? lastUserMsg.image_ids : null,
          }).catch(() => {})
        }
        postJSON(`${API.chatSessions}/${sid}/messages`, {
          role: 'assistant', content: textRef.current, thinking: thinkingRef.current || null,
        }).then(() => loadSessions()).catch(() => {})
      }
    }
    prevStreamingRef.current = isStreaming
  }, [isStreaming]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleNewSession() {
    setMessages([])
    setActiveSessionId(null)
    setPendingImages([])
  }

  async function loadSession(id) {
    try {
      const data = await fetchJSON(`${API.chatSessions}/${id}/messages`)
      setMessages((data?.messages || []).map(m => ({
        role: m.role, content: m.content, thinking: m.thinking,
        image_ids: m.image_ids || [],
      })))
      setActiveSessionId(id)
      setPendingImages([])
    } catch {
      toast('세션 불러오기 실패', 'error')
    }
  }

  async function handleDeleteSession(id) {
    try {
      await fetchJSON(`${API.chatSessions}/${id}`, { method: 'DELETE' })
      if (activeSessionId === id) { setMessages([]); setActiveSessionId(null) }
      loadSessions()
      toast('대화 삭제됨', 'success')
    } catch {
      toast('삭제 실패', 'error')
    }
  }

  const doSend = useCallback((msg, history, imageIds = []) => {
    sendMessage({
      message: msg,
      model,
      reasoning_level: reasoning,
      deep_mode: deepMode,
      history: history.slice(-10).map(m => ({
        role: m.role, content: m.content,
        image_ids: m.image_ids || [],
      })),
      image_ids: imageIds,
    })
  }, [model, reasoning, deepMode, sendMessage])

  const handleSend = useCallback(async () => {
    const hasImages = pendingImages.length > 0
    if ((!input.trim() && !hasImages) || isStreaming) return
    // Auto-create session if needed
    if (!activeSessionRef.current) {
      try {
        const s = await postJSON(API.chatSessions, { title: '', model })
        setActiveSessionId(s.id)
        activeSessionRef.current = s.id
      } catch { /* proceed without session */ }
    }
    const imageIds = pendingImages.map(img => img.id)
    const userMsg = { role: 'user', content: input, image_ids: imageIds }
    setMessages(m => [...m, userMsg])
    doSend(input, messages, imageIds)
    setInput('')
    setPendingImages([])
    // Auto-resize reset
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setTimeout(() => textareaRef.current?.focus(), 0)
  }, [input, isStreaming, messages, doSend, model, pendingImages])

  const handleRegenerate = useCallback(() => {
    if (isStreaming || messages.length < 2) return
    let lastUserIdx = -1
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') { lastUserIdx = i; break }
    }
    if (lastUserIdx < 0) return
    const lastUser = messages[lastUserIdx]
    const trimmed = messages.slice(0, lastUserIdx + 1)
    setMessages(trimmed)
    doSend(lastUser.content, trimmed.slice(0, -1), lastUser.image_ids || [])
  }, [isStreaming, messages, doSend])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleTextareaChange(e) {
    setInput(e.target.value.slice(0, MAX_INPUT))
    e.target.style.height = 'auto'
    e.target.style.height = e.target.scrollHeight + 'px'
  }

  function handleExampleClick(prompt) {
    setInput(prompt)
    setTimeout(() => textareaRef.current?.focus(), 0)
  }

  async function handleImageUpload(e) {
    const files = Array.from(e.target.files || [])
    if (!files.length) return
    // Ensure session exists for image upload
    let sid = activeSessionRef.current
    if (!sid) {
      try {
        const s = await postJSON(API.chatSessions, { title: '', model })
        setActiveSessionId(s.id)
        activeSessionRef.current = s.id
        sid = s.id
      } catch { return }
    }
    setUploading(true)
    for (const file of files) {
      if (file.size > 10 * 1024 * 1024) {
        toast('이미지 크기가 10MB를 초과합니다', 'error')
        continue
      }
      const formData = new FormData()
      formData.append('file', file)
      formData.append('session_id', String(sid))
      try {
        const res = await fetch(`${API.chat}/upload-image`, { method: 'POST', body: formData })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || `HTTP ${res.status}`)
        }
        const data = await res.json()
        const previewUrl = URL.createObjectURL(file)
        setPendingImages(prev => [...prev, { id: data.image_id, filename: data.filename, previewUrl }])
      } catch (err) {
        toast(`이미지 업로드 실패: ${err.message}`, 'error')
      }
    }
    setUploading(false)
    // Reset file input so same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function handleSaveHwpx() {
    if (messages.length === 0) return
    try {
      const res = await fetch(`${API.chat}/save-hwpx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const cd = res.headers.get('content-disposition') || ''
      const match = cd.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/)
      const filename = match ? decodeURIComponent(match[1]) : `채팅내용_${Date.now()}.hwpx`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
      toast('HWPX 다운로드 완료', 'success')
    } catch (e) {
      toast(`저장 실패: ${e.message}`, 'error')
    }
  }

  async function handleCopyMessage(content, idx) {
    await navigator.clipboard.writeText(content)
    setCopiedIdx(idx)
    toast('복사 완료', 'success')
    setTimeout(() => setCopiedIdx(null), 2000)
  }

  function handleClear() {
    if (isStreaming) return
    setClearConfirm(true)
  }

  return (
    <div className="page-chat">
      <ConfirmModal
        open={clearConfirm}
        title="대화 초기화"
        message="대화 내용이 모두 삭제됩니다. 계속하시겠습니까?"
        confirmLabel="초기화"
        danger
        onConfirm={() => { setMessages([]); setActiveSessionId(null); setClearConfirm(false) }}
        onCancel={() => setClearConfirm(false)}
      />
      <ConfirmModal
        open={!!deleteConfirm}
        title="대화 삭제"
        message="이 대화를 삭제하시겠습니까?"
        confirmLabel="삭제"
        danger
        onConfirm={() => { handleDeleteSession(deleteConfirm); setDeleteConfirm(null) }}
        onCancel={() => setDeleteConfirm(null)}
      />

      <div className="page-header">
        <h2>AI 채팅</h2>
        <div className="page-actions">
          <button className="btn btn-secondary" onClick={handleClear} disabled={messages.length === 0 || isStreaming}>
            대화 초기화
          </button>
          <button className="btn btn-secondary" onClick={handleSaveHwpx} disabled={messages.length === 0 || isStreaming}>
            HWPX 저장
          </button>
        </div>
      </div>

      {sessions.length > 0 && (
        <div className="chat-sessions-bar">
          <button className="btn btn-sm btn-primary" onClick={handleNewSession}>새 대화</button>
          <div className="chat-sessions-list">
            {sessions.map(s => (
              <div key={s.id} className={`chat-session-chip ${s.id === activeSessionId ? 'active' : ''}`}>
                <button className="chat-session-btn" onClick={() => loadSession(s.id)}>
                  <span className="chat-session-title">{s.title || '새 대화'}</span>
                  <span className="chat-session-time">{timeAgo(s.updated_at)}</span>
                </button>
                <button className="chat-session-del" onClick={e => { e.stopPropagation(); setDeleteConfirm(s.id) }}>&times;</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="chat-config">
        <div className="form-group" style={{ flex: 1 }}>
          <label>추론 수준</label>
          <div className="reasoning-slider">
            {['low', 'medium', 'high'].map(level => (
              <button
                key={level}
                className={`btn btn-sm ${reasoning === level ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setReasoning(level)}
              >
                {REASONING_LABELS[level]}
              </button>
            ))}
          </div>
        </div>
        <div className="form-group" style={{ flex: 1 }}>
          <label>심층 분석</label>
          <button
            className={`btn btn-sm ${deepMode ? 'btn-accent' : 'btn-secondary'}`}
            onClick={() => setDeepMode(d => !d)}
          >
            {deepMode ? '심층 분석 ON' : '심층 분석 OFF'}
          </button>
        </div>
        <div className="form-group" style={{ flex: 2 }}>
          <label>모델</label>
          <ModelSelector value={model} onChange={setModel} />
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && !isStreaming && (
          <div className="chat-empty-state">
            <div className="empty-title">AI 공문서 어시스턴트</div>
            <div className="empty-subtitle">무엇을 도와드릴까요?</div>
            <div className="example-prompts">
              {EXAMPLE_PROMPTS.map((p, i) => (
                <button key={i} className="example-prompt" onClick={() => handleExampleClick(p)}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          const isLastAi = msg.role === 'assistant' && i === messages.length - 1
          return (
            <div key={i} className={`chat-bubble ${msg.role}`}>
              <div className="chat-role">{msg.role === 'user' ? '사용자' : 'AI'}</div>
              {msg.image_ids?.length > 0 && (
                <div className="chat-message-images">
                  {msg.image_ids.map(imgId => (
                    <img
                      key={imgId}
                      src={`${API.chat}/images/${imgId}`}
                      alt="첨부 이미지"
                      className="chat-message-image"
                      onClick={() => window.open(`${API.chat}/images/${imgId}`, '_blank')}
                    />
                  ))}
                </div>
              )}
              {msg.thinking && <ThinkingPanel content={msg.thinking} />}
              <div className="chat-text markdown-body">
                {msg.role === 'assistant'
                  ? <ReactMarkdown>{msg.content}</ReactMarkdown>
                  : msg.content
                }
              </div>
              {msg.role === 'assistant' && !isStreaming && (
                <div className="chat-actions">
                  <button className="btn-icon" onClick={() => handleCopyMessage(msg.content, i)} title="복사">
                    {copiedIdx === i ? '\u2714' : '\u2398'}
                  </button>
                  {isLastAi && (
                    <button className="btn-icon" onClick={handleRegenerate} title="다시 생성">&#x21BB;</button>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {isStreaming && (
          <div className="chat-bubble assistant">
            <div className="chat-role">AI</div>
            {modelSwitchNotice && (
              <div className="chat-model-switch-notice">Vision 모델 자동 선택: {modelSwitchNotice}</div>
            )}
            {fetchedUrls.length > 0 && (
              <div className="chat-fetched-urls">
                {fetchedUrls.map((f, i) => (
                  <div key={i} className="fetched-url-item">
                    <span className="fetched-url-icon">{f.status.includes('차단') ? '\u26A0' : '\u2714'}</span>
                    <span className="fetched-url-text">{f.status}</span>
                  </div>
                ))}
              </div>
            )}
            {thinking && <ThinkingPanel content={thinking} streaming />}
            {!thinking && !text && (
              <div className="chat-status-indicator">
                <span className="status-dot" />
                <span>응답 준비 중...{elapsed > 0 && ` (${elapsed}초)`}</span>
                {elapsed >= 15 && (
                  <div className="chat-status-hint">AI 모델이 응답을 준비 중입니다. 잠시 기다려 주세요.</div>
                )}
              </div>
            )}
            {text && (
              <div className="chat-text markdown-body">
                <ReactMarkdown>{text}</ReactMarkdown>
                <span className="cursor-blink">|</span>
              </div>
            )}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="chat-input-bar">
        {pendingImages.length > 0 && (
          <div className="chat-image-previews">
            {pendingImages.map((img, i) => (
              <div key={img.id} className="chat-image-preview">
                <img src={img.previewUrl} alt={img.filename} />
                <button
                  className="chat-image-remove"
                  onClick={() => setPendingImages(prev => prev.filter((_, idx) => idx !== i))}
                  title="삭제"
                >&times;</button>
              </div>
            ))}
          </div>
        )}
        <div className="chat-input-row">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            multiple
            style={{ display: 'none' }}
            onChange={handleImageUpload}
          />
          <div className="chat-input-wrap">
            <button
              className="chat-attach-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={isStreaming || uploading}
              title="이미지 첨부"
            >
              {uploading ? '\u23F3' : '\uD83D\uDCCE'}
            </button>
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder="메시지를 입력하세요..."
              disabled={isStreaming}
            />
            <span className={`chat-char-counter ${input.length >= MAX_INPUT ? 'char-counter-red' : input.length >= MAX_INPUT * 0.8 ? 'char-counter-amber' : ''}`}>
              {input.length}/{MAX_INPUT}
            </span>
          </div>
          {isStreaming ? (
            <button className="btn btn-danger" onClick={stop}>중지</button>
          ) : (
            <button className="btn btn-primary" onClick={handleSend} disabled={!input.trim() && pendingImages.length === 0}>전송</button>
          )}
        </div>
      </div>
    </div>
  )
}
