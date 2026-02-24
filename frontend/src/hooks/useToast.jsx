/** 토스트 알림 훅 + Provider */
import { createContext, useContext, useState, useCallback } from 'react'

const ToastContext = createContext(null)

const DISMISS_MS = { success: 3000, info: 4000, warning: 6000, error: 0 }

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts(t => t.filter(toast => toast.id !== id))
  }, [])

  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, message, type }])
    const ms = DISMISS_MS[type] ?? 4000
    if (ms > 0) {
      setTimeout(() => removeToast(id), ms)
    }
  }, [removeToast])

  return (
    <ToastContext.Provider value={addToast}>
      {children}
      <div className="toast-container" role="status" aria-live="polite">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <span className="toast-message">{t.message}</span>
            <button
              className="toast-close"
              onClick={() => removeToast(t.id)}
              aria-label="닫기"
            >&times;</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
