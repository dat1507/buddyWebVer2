import { AdminEventStatisticsPage } from '@/pages/admin/admin-event-statistics-page'
import { lazy, Suspense, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, Route, Routes } from 'react-router'

import { AdminLayout } from '@/components/layout/admin-layout'
import { PublicLayout } from '@/components/layout/public-layout'
import { UserLayout } from '@/components/layout/user-layout'
import { AdminLoginPage } from '@/pages/public/admin-login-page'
import { AdminUserDetailPage } from '@/pages/admin/admin-user-detail-page'
import { AdminEventCreatePage } from '@/pages/admin/admin-event-create-page'
import { AdminEventEditPage } from '@/pages/admin/admin-event-edit-page'
import { LandingPage } from '@/pages/public/landing-page'
import { CommunityComingSoonPage } from '@/pages/public/community-coming-soon-page'
import { EventDetailPage } from '@/pages/public/event-detail-page'
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
import { adminEventsEnabled, publicEventsEnabled } from '@/config/launch-scope'
import { ChatbotEntry } from '@/features/chatbot/chatbot-entry'

const RecapGalleryPage = lazy(() =>
  import('@/pages/public/recap-pages').then((module) => ({ default: module.RecapGalleryPage })),
)
const RecapDetailPage = lazy(() =>
  import('@/pages/public/recap-pages').then((module) => ({ default: module.RecapDetailPage })),
)
const AdminRecapsPage = lazy(() =>
  import('@/pages/admin/admin-recap-pages').then((module) => ({ default: module.AdminRecapsPage })),
)
const AdminRecapEditorPage = lazy(() =>
  import('@/pages/admin/admin-recap-pages').then((module) => ({
    default: module.AdminRecapEditorPage,
  })),
)
function RecapBoundary({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <Suspense
      fallback={
        <p role="status" className="p-8">
          {t('recaps.loading')}
        </p>
      }
    >
      {children}
    </Suspense>
  )
}

function App() {
  return (
    <>
      <SessionControls />
      <Routes>
        <Route path="adminLogin" element={<AdminLoginPage />} />
        <Route element={<PublicLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="login" element={<UserLoginPage />} />
          <Route path="register" element={<UserRegistrationPage />} />
          <Route path="verify-email" element={<EmailVerificationPage />} />
          <Route
            path="events/recap"
            element={
              <RecapBoundary>
                <RecapGalleryPage />
              </RecapBoundary>
            }
          />
          <Route
            path="events/recap/:recapId"
            element={
              <RecapBoundary>
                <RecapDetailPage />
              </RecapBoundary>
            }
          />
          <Route path="merchandise" element={<CommunityComingSoonPage feature="merchandise" />} />
          {publicEventsEnabled ? (
            <Route path="events/:eventId" element={<EventDetailPage />} />
          ) : (
            <Route path="events/*" element={<NotFoundPage />} />
          )}
        </Route>

        <Route element={<RoleGuard requiredRole="USER" />}>
          <Route path="user" element={<UserLayout />}>
            <Route index element={<Navigate to="dashboard" replace />} />
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
            <Route path="events/*" element={<NotFoundPage embedded />} />
          </Route>
        </Route>

        <Route element={<RoleGuard requiredRole="ADMIN" loginPath="/adminLogin" />}>
          <Route path="admin" element={<AdminLayout />}>
            <Route index element={<Navigate to="users" replace />} />
            {['dashboard', 'announcements', 'campus', 'analytics'].map((path) => (
              <Route key={path} path={path} element={<Navigate to="/admin/users" replace />} />
            ))}
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
            {adminEventsEnabled ? (
              <>
                <Route path="events/statistics" element={<AdminEventStatisticsPage />} />
                <Route path="events/new" element={<AdminEventCreatePage />} />
                <Route
                  path="events/recaps"
                  element={
                    <RecapBoundary>
                      <AdminRecapsPage />
                    </RecapBoundary>
                  }
                />
                <Route
                  path="events/recaps/new"
                  element={
                    <RecapBoundary>
                      <AdminRecapEditorPage />
                    </RecapBoundary>
                  }
                />
                <Route
                  path="events/recaps/:recapId/edit"
                  element={
                    <RecapBoundary>
                      <AdminRecapEditorPage />
                    </RecapBoundary>
                  }
                />
                <Route
                  path="events/recaps/:recapId/preview"
                  element={
                    <RecapBoundary>
                      <AdminRecapEditorPage preview />
                    </RecapBoundary>
                  }
                />
                <Route path="events/:eventId/edit" element={<AdminEventEditPage />} />
              </>
            ) : (
              <Route path="events/*" element={<NotFoundPage embedded />} />
            )}
            <Route path="users/:userId" element={<AdminUserDetailPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      <ChatbotEntry />
    </>
  )
}

export default App
