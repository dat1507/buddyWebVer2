import type { ComponentType } from 'react'

import type { ProfileReadinessRequirement } from '@/features/profile/profile-readiness-gate'
import { OnboardingIdentityPage } from '@/pages/user/onboarding-identity-page'
import { OnboardingInterestsPage } from '@/pages/user/onboarding-interests-page'
import { OnboardingPreferencesPage } from '@/pages/user/onboarding-preferences-page'
import { ProfilePage } from '@/pages/user/profile-page'
import { ProfileEditPage } from '@/pages/user/profile-edit-page'
import { SettingsPage } from '@/pages/user/settings-page'

type UserRoutePath =
  | 'profile'
  | 'profile/edit'
  | 'onboarding'
  | 'onboarding/interests'
  | 'onboarding/preferences'
  | 'matching'
  | 'buddy'
  | 'assistant'
  | 'campus'
  | 'events'
  | 'settings'

type UserRoute = {
  path: UserRoutePath
  title: string
  readiness?: ProfileReadinessRequirement
} & ({ kind: 'placeholder' } | { kind: 'page'; Component: ComponentType })

// Routing and navigation share delivery status. Add a page component only when its task is done.
const userRoutes: readonly UserRoute[] = [
  { path: 'profile', title: 'Profile', kind: 'page', Component: ProfilePage },
  { path: 'profile/edit', title: 'Edit profile', kind: 'page', Component: ProfileEditPage },
  {
    path: 'onboarding',
    title: 'Profile setup',
    readiness: 'incomplete',
    kind: 'page',
    Component: OnboardingIdentityPage,
  },
  {
    path: 'onboarding/interests',
    title: 'Profile interests and languages',
    readiness: 'incomplete',
    kind: 'page',
    Component: OnboardingInterestsPage,
  },
  {
    path: 'onboarding/preferences',
    title: 'Profile availability and preferences',
    readiness: 'incomplete',
    kind: 'page',
    Component: OnboardingPreferencesPage,
  },
  {
    path: 'matching',
    title: 'Buddy matching',
    readiness: 'matchingEligible',
    kind: 'placeholder',
  },
  { path: 'buddy', title: 'My Buddy', kind: 'placeholder' },
  { path: 'assistant', title: 'AI assistant', kind: 'placeholder' },
  { path: 'campus', title: 'Campus', kind: 'placeholder' },
  { path: 'events', title: 'Events', kind: 'placeholder' },
  { path: 'settings', title: 'Settings', kind: 'page', Component: SettingsPage },
]

export { userRoutes }
export type { UserRoutePath }
