import { z } from 'zod'

import { ApiError } from '@/lib/api'

const profileMissingFieldSchema = z.enum([
  'FULL_NAME',
  'STUDENT_TYPE',
  'AVATAR',
  'INTERESTS',
  'LANGUAGES',
])

const matchingIneligibilityReasonSchema = z.enum([
  'PROFILE_INCOMPLETE',
  'ACCOUNT_INACTIVE',
  'ACCOUNT_DELETED',
  'EMAIL_VERIFICATION_REQUIRED',
  'MATCHING_OPT_IN_REQUIRED',
  'ACTIVE_MATCH_RESERVATION',
])

const profileCompletionSchema = z.object({
  status: z.enum(['INCOMPLETE', 'COMPLETE']),
  percentage: z.number().int().min(0).max(100),
  missing_fields: z.array(profileMissingFieldSchema).max(5),
  matching_eligible: z.boolean(),
  reasons: z.array(matchingIneligibilityReasonSchema).max(6),
})

type ProfileCompletion = Readonly<z.infer<typeof profileCompletionSchema>>
type ProfileMissingField = z.infer<typeof profileMissingFieldSchema>
type MatchingIneligibilityReason = z.infer<typeof matchingIneligibilityReasonSchema>

function parseMatchingIneligibilityReason(payload: unknown): MatchingIneligibilityReason {
  const result = matchingIneligibilityReasonSchema.safeParse(payload)
  if (!result.success) throw new ApiError(200, 'invalidResponse')
  return result.data
}

function parseProfileCompletion(payload: unknown): ProfileCompletion {
  const result = profileCompletionSchema.safeParse(payload)
  if (!result.success) throw new ApiError(200, 'invalidResponse')
  return Object.freeze(result.data)
}

export { parseMatchingIneligibilityReason, parseProfileCompletion }
export type { MatchingIneligibilityReason, ProfileCompletion, ProfileMissingField }
