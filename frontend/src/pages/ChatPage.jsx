import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { API } from '../utils/api'
import { useWebSocket } from '../hooks/useWebSocket'
import ModelSelector from '../components/ModelSelector'
import ThinkingPanel from '../components/ThinkingPanel'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../hooks/useToast'

const REASONING_LABELS = { low: '빠른 답변', medium: '균형', high: '깊은 분석' }
const MAX_INPUT = 2000

const EXAMPLE_PROMPTS = [
  '기안문 초안 작성 방법을 알려줘',
  '회의록 양식 예시를 보여줘',
  '민원 답변서 작성 시 유의사항은?',
  '광명시 주요 사업 계획서를 작성해줘',
]

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [model, setModel] = useState(null)
  const [reasoning, setReasoning] = useState('medium')
  const [deepMode, setDeepMode] = useState(false)
  const [clearConfirm, setClearConfirm] = useState(false)
  const toast = useToast()
  const { text, thinking, fetchedUrls, isStreaming, sendMessage, stop } = useWebSocket(
    API.chatStream,
    { onError: (msg) => toast(msg, 'error') },
  )
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  const textRef = useRef(text)
  const thinkingRef = useRef(thinking)
  textRef.current = text
  thinkingRef.current = thinking

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, text, thinking])

  useEffect(() => {
    if (!isStreaming && textRef.current) {
      setMessages(m => [...m, { role: 'assistant', content: textRef.current, thinking: thinkingRef.current }])
    }
  }, [isStreaming])

  const doSend = useCallback((msg, history) => {
    sendMessage({
      message: msg,
      model,
      reasoning_level: reasoning,
      deep_mode: deepMode,
      history: history.slice(-10),
    })
  }, [model, reasoning, deepMode, sendMessage])

  const handleSend = useCallback(() => {
    if (!input.trim() || isStreaming) return
    const userMsg = { role: 'user', content: input }
    setMessages(m => [...m, userMsg])
    doSend(input, messages)
    setInput('')
    // Auto-resize reset
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setTimeout(() => textareaRef.current?.focus(), 0)
  }, [input, isStreaming, messages, doSend])

  const handleRegenerate = useCallback(() => {
    if (isStreaming || messages.length < 2) return
    let lastUserIdx = -1
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') { lastUserIdx = i; break }
    }
    if (lastUserIdx < 0) return
    const lastUserMsg = messages[lastUserIdx].content
    const trimmed = messages.slice(0, lastUserIdx + 1)
    setMessages(trimmed)
    doSend(lastUserMsg, trimmed.slice(0, -1))
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
        onConfirm={() => { setMessages([]); setClearConfirm(false) }}
        onCancel={() => setClearConfirm(false)}
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
              {msg.thinking && <ThinkingPanel content={msg.thinking} />}
              <div className="chat-text markdown-body">
                {msg.role === 'assistant'
                  ? <ReactMarkdown>{msg.content}</ReactMarkdown>
                  : msg.content
                }
              </div>
              {isLastAi && !isStreaming && (
                <div className="chat-actions">
                  <button className="btn-icon" onClick={handleRegenerate} title="다시 생성">&#x21BB;</button>
                </div>
              )}
            </div>
          )
        })}

        {isStreaming && (
          <div className="chat-bubble assistant">
            <div className="chat-role">AI</div>
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
                <span>응답 준비 중...</span>
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
        <div className="chat-input-wrap">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="메시지를 입력하세요... (Enter로 전송, Shift+Enter로 줄바꿈)"
            disabled={isStreaming}
          />
          <span className={`chat-char-counter ${input.length >= MAX_INPUT ? 'char-counter-red' : input.length >= MAX_INPUT * 0.8 ? 'char-counter-amber' : ''}`}>
            {input.length}/{MAX_INPUT}
          </span>
        </div>
        {isStreaming ? (
          <button className="btn btn-danger" onClick={stop}>중지</button>
        ) : (
          <button className="btn btn-primary" onClick={handleSend} disabled={!input.trim()}>전송</button>
        )}
      </div>
    </div>
  )
}
