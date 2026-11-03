import { lazy, Suspense } from 'react'
import { useLocation } from 'react-router'

import { useAuthStore } from '@/stores/auth-store'
import { ChatbotBoundary } from './chatbot-boundary'

const ChatbotWidget = lazy(() => import('./chatbot-widget'))

function ChatbotEntry() {
  const { pathname } = useLocation()
  const user = useAuthStore((state) => state.user)
  const publicRoute =
    pathname === '/' ||
    /^\/(login|register|verify-email|merchandise)\/?$/.test(pathname) ||
    /^\/events\//.test(pathname)
  const userRoute = /^\/user(?:\/|$)/.test(pathname) && user?.role === 'USER'
  if (
    import.meta.env.VITE_CHATBOT_ENABLED !== 'true' ||
    user?.role === 'ADMIN' ||
    (!publicRoute && !userRoute)
  )
    return null
  return (
    <ChatbotBoundary key={user?.id ?? 'public'}>
      <Suspense fallback={null}>
        <ChatbotWidget />
      </Suspense>
    </ChatbotBoundary>
  )
}

export { ChatbotEntry }
