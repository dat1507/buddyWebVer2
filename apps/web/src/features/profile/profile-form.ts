import type { OwnProfile } from '@/features/profile/profile'

type ProfileFormMode = 'onboarding' | 'edit'
type ReloadOwnProfile = () => Promise<OwnProfile | undefined>

export type { ProfileFormMode, ReloadOwnProfile }
