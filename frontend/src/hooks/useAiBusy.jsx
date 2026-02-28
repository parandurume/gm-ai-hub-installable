/** 글로벌 AI 처리 상태 컨텍스트 */
import { createContext, useContext, useState, useCallback } from 'react'

const AiBusyContext = createContext({
  busy: false,
  taskLabel: null,
  setBusy: () => {},
  clearBusy: () => {},
})

export function AiBusyProvider({ children }) {
  const [state, setState] = useState({ busy: false, taskLabel: null })
  const setBusy = useCallback((label) => setState({ busy: true, taskLabel: label }), [])
  const clearBusy = useCallback(() => setState({ busy: false, taskLabel: null }), [])

  return (
    <AiBusyContext.Provider value={{ ...state, setBusy, clearBusy }}>
      {children}
    </AiBusyContext.Provider>
  )
}

export function useAiBusy() {
  return useContext(AiBusyContext)
}
