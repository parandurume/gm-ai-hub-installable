import { lazy, Suspense, useState, useCallback, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import { ToastProvider } from './hooks/useToast'
import { AiBusyProvider } from './hooks/useAiBusy'
import { TourProvider, useTour } from './hooks/useTour'
import TourOverlay from './components/TourOverlay'
import LoadingSpinner from './components/LoadingSpinner'
import { fetchJSON, API } from './utils/api'

/* bundle-dynamic-imports: Route-based code splitting via React.lazy.
   Each page loads only when navigated to, reducing initial bundle. */
const Dashboard = lazy(() => import('./pages/Dashboard'))
const FilesPage = lazy(() => import('./pages/FilesPage'))
const DraftPage = lazy(() => import('./pages/DraftPage'))
const SearchPage = lazy(() => import('./pages/SearchPage'))
const MeetingPage = lazy(() => import('./pages/MeetingPage'))
const ComplaintPage = lazy(() => import('./pages/ComplaintPage'))
const RegulationPage = lazy(() => import('./pages/RegulationPage'))
const PiiPage = lazy(() => import('./pages/PiiPage'))
const DiffPage = lazy(() => import('./pages/DiffPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const SetupWizard = lazy(() => import('./pages/SetupWizard'))

function SetupGuard({ children }) {
  const [status, setStatus] = useState('loading') // loading | setup | ready
  const location = useLocation()
  const navigate = useNavigate()
  const { startTour, isCompleted: tourCompleted } = useTour()

  useEffect(() => {
    fetchJSON(API.setupStatus)
      .then(data => {
        setStatus(data.setup_completed ? 'ready' : 'setup')
      })
      .catch(() => {
        // API 실패 시 (DB 미초기화 등) 셋업으로
        setStatus('setup')
      })
  }, [])

  useEffect(() => {
    if (status === 'setup' && location.pathname !== '/setup') {
      navigate('/setup', { replace: true })
    }
  }, [status, location.pathname, navigate])

  // 최초 실행 시 가이드 투어 자동 시작
  useEffect(() => {
    if (status === 'ready' && !tourCompleted && location.pathname !== '/setup') {
      const timer = setTimeout(() => startTour(), 500)
      return () => clearTimeout(timer)
    }
  }, [status]) // eslint-disable-line react-hooks/exhaustive-deps

  if (status === 'loading') return <LoadingSpinner />
  return children
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const closeSidebar = useCallback(() => setSidebarOpen(false), [])
  const toggleSidebar = useCallback(() => setSidebarOpen(o => !o), [])

  return (
    <BrowserRouter>
      <ToastProvider>
        <AiBusyProvider>
        <TourProvider>
        <SetupGuard>
          <Suspense fallback={<LoadingSpinner />}>
            <Routes>
              <Route path="/setup" element={<SetupWizard />} />
              <Route path="*" element={
                <div className="app-layout">
                  <Sidebar open={sidebarOpen} onClose={closeSidebar} />
                  {sidebarOpen && <div className="sidebar-backdrop" onClick={closeSidebar} />}
                  <div className="main-area">
                    <Topbar onToggleSidebar={toggleSidebar} />
                    <main className="content">
                      <Suspense fallback={<LoadingSpinner />}>
                        <Routes>
                          <Route path="/" element={<Dashboard />} />
                          <Route path="/files" element={<FilesPage />} />
                          <Route path="/draft" element={<DraftPage />} />
                          <Route path="/search" element={<SearchPage />} />
                          <Route path="/meeting" element={<MeetingPage />} />
                          <Route path="/complaint" element={<ComplaintPage />} />
                          <Route path="/regulation" element={<RegulationPage />} />
                          <Route path="/pii" element={<PiiPage />} />
                          <Route path="/diff" element={<DiffPage />} />
                          <Route path="/chat" element={<ChatPage />} />
                          <Route path="/settings" element={<SettingsPage />} />
                        </Routes>
                      </Suspense>
                    </main>
                  </div>
                  <TourOverlay />
                </div>
              } />
            </Routes>
          </Suspense>
        </SetupGuard>
        </TourProvider>
        </AiBusyProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}
