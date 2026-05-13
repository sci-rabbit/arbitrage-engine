import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../../store/auth'

export function AccessRoute() {
  const { isAuthenticated, hasAccess } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!hasAccess) return <Navigate to="/pricing" replace />
  return <Outlet />
}