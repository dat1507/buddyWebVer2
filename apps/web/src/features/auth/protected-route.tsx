import { useTranslation } from 'react-i18next'
import { Navigate, Outlet, useLocation } from 'react-router'

import { useAuthStore } from '@/stores/auth-store'

interface ProtectedRouteProps {
  loginPath?: '/login' | '/adminLogin'
}

function ProtectedRoute({ loginPath = '/login' }: ProtectedRouteProps) {
  const status = useAuthStore((state) => state.status)
  const location = useLocation()
  const { t } = useTranslation()

  // Bootstrap owns verification/refresh. Never mount private children before it resolves.
  if (status === 'unknown' || status === 'loading') {
    return (
      <main
        aria-busy="true"
        className="flex min-h-screen items-center justify-center bg-background px-6 text-foreground"
      >
        <p role="status">{t('auth.guard.pending')}</p>
      </main>
    )
  }

  if (status === 'unauthenticated') {
    return (
      <Navigate
        to={loginPath}
        replace
        state={{
          from: { pathname: location.pathname, search: location.search, hash: location.hash },
        }}
      />
    )
  }

  // Authentication UX only. RoleGuard and backend authorization enforce separate boundaries.
  return <Outlet />
}

export { ProtectedRoute }
