/** gpt-oss 스트리밍 채팅 훅 — single persistent connection */
import { useState, useRef, useCallback, useEffect } from 'react'

export function useWebSocket(url, { onError } = {}) {
  const [tokens, setTokens] = useState([])
  const [thinking, setThinking] = useState('')
  const [fetchedUrls, setFetchedUrls] = useState([])
  const [modelSwitch, setModelSwitch] = useState(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const ws = useRef(null)
  const pendingPayload = useRef(null)
  const onErrorRef = useRef(onError)
  onErrorRef.current = onError

  const connect = useCallback(() => {
    if (ws.current && ws.current.readyState <= WebSocket.OPEN) return

    const socket = new WebSocket(url)
    ws.current = socket

    socket.onopen = () => {
      if (pendingPayload.current) {
        socket.send(JSON.stringify(pendingPayload.current))
        pendingPayload.current = null
      }
    }

    socket.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'token') {
        setTokens(t => [...t, data.content])
      } else if (data.type === 'thinking') {
        setThinking(t => t + data.content)
      } else if (data.type === 'fetching') {
        setFetchedUrls(f => [...f, { url: data.url, status: data.status }])
      } else if (data.type === 'model_switch') {
        setModelSwitch(data.model)
      } else if (data.type === 'done') {
        setIsStreaming(false)
      } else if (data.type === 'error') {
        setIsStreaming(false)
        onErrorRef.current?.(data.message || 'AI 응답 오류가 발생했습니다.')
      }
    }

    socket.onerror = () => {
      setIsStreaming(false)
      onErrorRef.current?.('서버 연결에 실패했습니다. Ollama가 실행 중인지 확인하세요.')
    }

    socket.onclose = () => {
      ws.current = null
      setIsStreaming(false)
    }
  }, [url])

  useEffect(() => {
    return () => {
      if (ws.current) {
        ws.current.onclose = null
        ws.current.close()
        ws.current = null
      }
    }
  }, [])

  const sendMessage = useCallback((payload) => {
    setTokens([])
    setThinking('')
    setFetchedUrls([])
    setModelSwitch(null)
    setIsStreaming(true)

    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(payload))
    } else {
      pendingPayload.current = payload
      connect()
    }
  }, [connect])

  const stop = useCallback(() => {
    if (ws.current) {
      ws.current.close()
      ws.current = null
    }
    setIsStreaming(false)
  }, [])

  return { text: tokens.join(''), thinking, fetchedUrls, modelSwitch, isStreaming, sendMessage, stop }
}
