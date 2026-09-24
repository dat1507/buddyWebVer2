import { describe, expect, it } from 'vitest'

import {
  parseMatchingIneligibilityReason,
  parseProfileCompletion,
} from '@/features/profile/profile-completion'
import { ApiError } from '@/lib/api'

describe('profile completion reason contract', () => {
  it('accepts the shared email-verification reason in the completion projection', () => {
    expect(parseMatchingIneligibilityReason('EMAIL_VERIFICATION_REQUIRED')).toBe(
      'EMAIL_VERIFICATION_REQUIRED',
    )
    expect(
      parseProfileCompletion({
        status: 'COMPLETE',
        percentage: 100,
        missing_fields: [],
        matching_eligible: false,
        reasons: ['EMAIL_VERIFICATION_REQUIRED'],
      }),
    ).toEqual({
      status: 'COMPLETE',
      percentage: 100,
      missing_fields: [],
      matching_eligible: false,
      reasons: ['EMAIL_VERIFICATION_REQUIRED'],
    })
  })

  it('rejects unknown client or server reason values without reflecting them', () => {
    const privateValue = 'test-only-private-reason'

    try {
      parseMatchingIneligibilityReason(privateValue)
      expect.fail('Expected an unknown reason to be rejected')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect(String(error)).not.toContain(privateValue)
      expect(JSON.stringify(error)).not.toContain(privateValue)
    }
  })
})
