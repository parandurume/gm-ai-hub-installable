import { lazy, Suspense, useState, useCallback } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import { ToastProvider } from './hooks/useToast'
import LoadingSpinner from './components/LoadingSpinner'

/* bundle-dynamic-imports: Route-based code splitting via React.lazy.
   Each page loads only when navigated to, reducing initial bundle. */
const Dashboard = lazy(() => import('./pages/Dashboard'))
const FilesPage = lazy(() => import('./pages/FilesPage'))
const GianmunPage = lazy(() => import('./pages/GianmunPage'))
const SearchPage = lazy(() => import('./pages/SearchPage'))
const MeetingPage = lazy(() => import('./pages/MeetingPage'))
const ComplaintPage = lazy(() => import('./pages/ComplaintPage'))
const RegulationPage = lazy(() => import('./pages/RegulationPage'))
const PiiPage = lazy(() => import('./pages/PiiPage'))
const DiffPage = lazy(() => import('./pages/DiffPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const closeSidebar = useCallback(() => setSidebarOpen(false), [])
  const toggleSidebar = useCallback(() => setSidebarOpen(o => !o), [])

  return (
    <BrowserRouter>
      <ToastProvider>
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
                  <Route path="/gianmun" element={<GianmunPage />} />
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
        </div>
      </ToastProvider>
    </BrowserRouter>
  )
}
