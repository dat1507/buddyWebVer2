import { Navigate, Outlet } from 'react-router'

import { ProtectedRoute } from '@/features/auth/protected-route'
import type { UserRole } from '@/features/auth/session-user'
import { useAuthStore } from '@/stores/auth-store'

interface RoleGuardProps {
  requiredRole: UserRole
  loginPath?: '/login' | '/adminLogin'
}

/** Presentation only; backend authorization always verifies the current database role. */
function RoleGuard({ requiredRole, loginPath = '/login' }: RoleGuardProps) {
  const status = useAuthStore((state) => state.status)
  const role = useAuthStore((state) => state.role)

  if (status !== 'authenticated') return <ProtectedRoute loginPath={loginPath} />
  if (role !== requiredRole) return <Navigate to="/" replace />

  return <Outlet />
}

export { RoleGuard }
