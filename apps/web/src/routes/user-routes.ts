import type { ComponentType } from 'react'

import { OnboardingIdentityPage } from '@/pages/user/onboarding-identity-page'

type UserRoutePath =
  | 'dashboard'
  | 'profile'
  | 'onboarding'
  | 'matching'
  | 'buddy'
  | 'assistant'
  | 'campus'
  | 'events'
  | 'settings'

type UserRoute = { path: UserRoutePath; title: string } & (
  { kind: 'placeholder' } | { kind: 'page'; Component: ComponentType }
)

// Routing and navigation share delivery status. Add a page component only when its task is done.
const userRoutes: readonly UserRoute[] = [
  { path: 'dashboard', title: 'Dashboard', kind: 'placeholder' },
  { path: 'profile', title: 'Profile', kind: 'placeholder' },
  { path: 'onboarding', title: 'Profile setup', kind: 'page', Component: OnboardingIdentityPage },
  { path: 'matching', title: 'Buddy matching', kind: 'placeholder' },
  { path: 'buddy', title: 'My Buddy', kind: 'placeholder' },
  { path: 'assistant', title: 'AI assistant', kind: 'placeholder' },
  { path: 'campus', title: 'Campus', kind: 'placeholder' },
  { path: 'events', title: 'Events', kind: 'placeholder' },
  { path: 'settings', title: 'Settings', kind: 'placeholder' },
]

export { userRoutes }
export type { UserRoutePath }
