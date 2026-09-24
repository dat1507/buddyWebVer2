import { Navigate, Route, Routes } from 'react-router'

import { AdminLayout } from '@/components/layout/admin-layout'
import { PublicLayout } from '@/components/layout/public-layout'
import { UserLayout } from '@/components/layout/user-layout'
import { AdminLoginPage } from '@/pages/public/admin-login-page'
import { LandingPage } from '@/pages/public/landing-page'
import { NotFoundPage } from '@/pages/not-found-page'
import { RoutePlaceholder } from '@/pages/route-placeholder'
import { UserLoginPage } from '@/pages/public/user-login-page'
import { UserRegistrationPage } from '@/pages/public/user-registration-page'
import { EmailVerificationPage } from '@/pages/public/email-verification-page'
import { SessionControls } from '@/features/auth/session-controls'
import { RoleGuard } from '@/features/auth/role-guard'
import { ProfileReadinessGate } from '@/features/profile/profile-readiness-gate'
import { adminRoutes } from '@/routes/admin-routes'
import { userRoutes } from '@/routes/user-routes'

function App() {
  return (
    <>
      <SessionControls />
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="adminLogin" element={<AdminLoginPage />} />
          <Route path="login" element={<UserLoginPage />} />
          <Route path="register" element={<UserRegistrationPage />} />
          <Route path="verify-email" element={<EmailVerificationPage />} />
        </Route>

        <Route element={<RoleGuard requiredRole="USER" />}>
          <Route path="user" element={<UserLayout />}>
            <Route index element={<Navigate to="profile/edit" replace />} />
            <Route path="dashboard" element={<Navigate to="/user/profile/edit" replace />} />
            {userRoutes.map((route) => {
              const page =
                route.kind === 'page' ? (
                  <route.Component />
                ) : (
                  <RoutePlaceholder area="User" title={route.title} />
                )
              return (
                <Route
                  key={route.path}
                  path={route.path}
                  element={
                    route.readiness ? (
                      <ProfileReadinessGate requirement={route.readiness}>
                        {page}
                      </ProfileReadinessGate>
                    ) : (
                      page
                    )
                  }
                />
              )
            })}
          </Route>
        </Route>

        <Route element={<RoleGuard requiredRole="ADMIN" loginPath="/adminLogin" />}>
          <Route path="admin" element={<AdminLayout />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            {adminRoutes.map((route) => (
              <Route
                key={route.path}
                path={route.path}
                element={
                  route.kind === 'page' ? (
                    <route.Component />
                  ) : (
                    <RoutePlaceholder area="Admin" title={route.title} />
                  )
                }
              />
            ))}
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </>
  )
}

export default App
