import type { ProfileCompletion } from '@/features/profile/profile-completion'

const completeProfileCompletion: ProfileCompletion = Object.freeze({
  status: 'COMPLETE',
  percentage: 100,
  missing_fields: [],
  matching_eligible: true,
  reasons: [],
})

const incompleteProfileCompletion = Object.freeze<ProfileCompletion>({
  status: 'INCOMPLETE',
  percentage: 0,
  missing_fields: ['FULL_NAME', 'STUDENT_TYPE', 'AVATAR', 'INTERESTS', 'LANGUAGES'],
  matching_eligible: false,
  reasons: ['PROFILE_INCOMPLETE', 'MATCHING_OPT_IN_REQUIRED'],
})

export { completeProfileCompletion, incompleteProfileCompletion }
