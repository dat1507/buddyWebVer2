import { Navigate, Route, Routes } from 'react-router'

import { AdminLayout } from '@/components/layout/admin-layout'
import { PublicLayout } from '@/components/layout/public-layout'
import { UserLayout } from '@/components/layout/user-layout'
import { LandingPage } from '@/pages/public/landing-page'
import { NotFoundPage } from '@/pages/not-found-page'
import { RoutePlaceholder } from '@/pages/route-placeholder'

const publicRoutes = [
  { path: 'login', title: 'User login' },
  { path: 'register', title: 'Create your account' },
  { path: 'adminLogin', title: 'Admin login' },
]

const userRoutes = [
  { path: 'dashboard', title: 'Dashboard' },
  { path: 'profile', title: 'Profile' },
  { path: 'matching', title: 'Buddy matching' },
  { path: 'buddy', title: 'My Buddy' },
  { path: 'assistant', title: 'AI assistant' },
  { path: 'campus', title: 'Campus' },
  { path: 'events', title: 'Events' },
  { path: 'settings', title: 'Settings' },
]

const adminRoutes = [
  { path: 'dashboard', title: 'Admin overview' },
  { path: 'users', title: 'User management' },
  { path: 'matching', title: 'Matching management' },
  { path: 'events', title: 'Event management' },
  { path: 'announcements', title: 'Announcements' },
  { path: 'knowledge-base', title: 'Knowledge base' },
  { path: 'campus', title: 'Campus management' },
  { path: 'analytics', title: 'Analytics' },
  { path: 'audit-log', title: 'Audit log' },
  { path: 'settings', title: 'Admin settings' },
]

function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<LandingPage />} />
        {publicRoutes.map(({ path, title }) => (
          <Route
            key={path}
            path={path}
            element={<RoutePlaceholder area="Public" title={title} />}
          />
        ))}
      </Route>

      <Route path="user" element={<UserLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        {userRoutes.map(({ path, title }) => (
          <Route key={path} path={path} element={<RoutePlaceholder area="User" title={title} />} />
        ))}
      </Route>

      <Route path="admin" element={<AdminLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        {adminRoutes.map(({ path, title }) => (
          <Route key={path} path={path} element={<RoutePlaceholder area="Admin" title={title} />} />
        ))}
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
