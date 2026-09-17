import { create } from 'zustand'

import { parseSessionUser } from '@/features/auth/session-user'
import type { SessionUser, UserRole } from '@/features/auth/session-user'

type SessionStatus = 'unknown' | 'loading' | 'authenticated' | 'unauthenticated'

type SessionState =
  | { status: 'authenticated'; user: SessionUser; role: UserRole }
  | { status: Exclude<SessionStatus, 'authenticated'>; user: null; role: null }

interface AuthActions {
  startLoading: () => void
  setAuthenticated: (payload: unknown) => void
  clearSession: () => void
  resetSession: () => void
}

type AuthStore = SessionState & AuthActions

// Client presentation only, never authorization. No persistence/devtools or transport side effects.
// AUTH-021 will bootstrap /api/auth/me and coordinate refresh/logout/private query caches.
const useAuthStore = create<AuthStore>()((set) => ({
  status: 'unknown',
  user: null,
  role: null,
  startLoading: () => set({ status: 'loading', user: null, role: null }),
  setAuthenticated: (payload) => {
    let user: SessionUser
    try {
      user = parseSessionUser(payload)
    } catch (error) {
      // Fail closed instead of leaving the previous account/role visible after invalid API data.
      set({ status: 'unauthenticated', user: null, role: null })
      throw error
    }
    set({ status: 'authenticated', user, role: user.role })
  },
  clearSession: () => set({ status: 'unauthenticated', user: null, role: null }),
  resetSession: () => set({ status: 'unknown', user: null, role: null }),
}))

export { useAuthStore }
export type { AuthStore, SessionState, SessionStatus }
