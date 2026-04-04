// ============================================================
// ГосДок — Корневой компонент: роутинг + protected routes
// ============================================================

import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { PageLoader } from '@/components/ui/Spinner'

// Страницы (lazy не используем для простоты диплома)
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import ForgotPassword from '@/pages/ForgotPassword'
import Dashboard from '@/pages/Dashboard'
import Workspaces from '@/pages/Workspaces'
import Documents from '@/pages/Documents'
import DocumentView from '@/pages/DocumentView'
import Tasks from '@/pages/Tasks'
import Reports from '@/pages/Reports'

// Protected route — редиректим на /login, если нет JWT
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) return <PageLoader />
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return <>{children}</>
}

// Public route — если уже авторизован, редиректим на /dashboard
function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) return <PageLoader />
  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      {/* Публичные маршруты */}
      <Route
        path="/login"
        element={<PublicRoute><Login /></PublicRoute>}
      />
      <Route
        path="/register"
        element={<PublicRoute><Register /></PublicRoute>}
      />
      <Route
        path="/forgot-password"
        element={<PublicRoute><ForgotPassword /></PublicRoute>}
      />

      {/* Защищённые маршруты */}
      <Route
        path="/dashboard"
        element={<ProtectedRoute><Dashboard /></ProtectedRoute>}
      />
      <Route
        path="/workspaces"
        element={<ProtectedRoute><Workspaces /></ProtectedRoute>}
      />
      <Route
        path="/documents"
        element={<ProtectedRoute><Documents /></ProtectedRoute>}
      />
      <Route
        path="/documents/:id"
        element={<ProtectedRoute><DocumentView /></ProtectedRoute>}
      />
      <Route
        path="/tasks"
        element={<ProtectedRoute><Tasks /></ProtectedRoute>}
      />
      <Route
        path="/reports"
        element={<ProtectedRoute><Reports /></ProtectedRoute>}
      />

      {/* Редиректы */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
