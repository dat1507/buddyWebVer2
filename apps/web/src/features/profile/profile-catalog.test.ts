import { describe, expect, it } from 'vitest'

import {
  parseActivityCatalog,
  parseProfilePreferenceSnapshot,
} from '@/features/profile/profile-catalog'
import { ApiError } from '@/lib/api'

const interestId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
const activityId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'

function validSnapshot() {
  return {
    version: 7,
    interest_ids: [interestId],
    custom_interests: [{ label: 'German' }],
    languages: [{ language_code: 'en', proficiency: 'fluent' }],
    custom_languages: [{ label: 'German', proficiency: 'intermediate' }],
    activity_ids: [activityId],
    custom_activities: [{ label: 'German' }],
  }
}

describe('PREF-004 profile preference response contracts', () => {
  it('parses the dedicated localized Activity catalog and rejects a locale mismatch', () => {
    expect(
      parseActivityCatalog(
        {
          locale: 'en',
          items: [{ id: activityId, code: 'board-games', label: 'Board Games' }],
        },
        'en',
      ),
    ).toEqual({
      locale: 'en',
      items: [{ id: activityId, code: 'board-games', label: 'Board Games' }],
    })

    expect(() =>
      parseActivityCatalog(
        {
          locale: 'en',
          items: [
            { id: activityId, code: 'board-games', label: 'Board Games', category: 'social' },
          ],
        },
        'de',
      ),
    ).toThrow(ApiError)
  })

  it('accepts the same normalized label in independent preference namespaces', () => {
    expect(parseProfilePreferenceSnapshot(validSnapshot())).toEqual(validSnapshot())
  })

  it('rejects normalized duplicates, combined limit overflow and invalid proficiency', () => {
    expect(() =>
      parseProfilePreferenceSnapshot({
        ...validSnapshot(),
        custom_interests: [{ label: 'Formula 1' }, { label: ' formula   1 ' }],
      }),
    ).toThrow(ApiError)

    expect(() =>
      parseProfilePreferenceSnapshot({
        ...validSnapshot(),
        interest_ids: Array.from(
          { length: 20 },
          (_, index) => `00000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`,
        ),
      }),
    ).toThrow(ApiError)

    expect(() =>
      parseProfilePreferenceSnapshot({
        ...validSnapshot(),
        custom_languages: [{ label: 'Swiss German', proficiency: 'expert' }],
      }),
    ).toThrow(ApiError)
  })
})
