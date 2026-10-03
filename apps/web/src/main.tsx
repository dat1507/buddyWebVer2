import { StrictMode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { queryClient } from '@/lib/query-client'
import { SessionBootstrap } from '@/features/auth/session-controls'
import { BuddyUnreadProvider } from '@/features/chat/buddy-unread'
import './i18n'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BuddyUnreadProvider>
        <BrowserRouter>
          <SessionBootstrap />
          <App />
        </BrowserRouter>
      </BuddyUnreadProvider>
    </QueryClientProvider>
  </StrictMode>,
)
