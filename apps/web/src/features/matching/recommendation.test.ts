import { describe, expect, it } from 'vitest'

import { parseRecommendationList } from '@/features/matching/recommendation'
import { ApiError } from '@/lib/api'
import { recommendationList } from '@/test/recommendations'

describe('REC-004 recommendation response contract', () => {
  it('accepts the current privacy-safe REC-003 response without changing server order', () => {
    const second = {
      ...recommendationList.items[0],
      profile: {
        ...recommendationList.items[0].profile,
        id: '44444444-4444-4444-8444-444444444444',
      },
      score: 42,
    }
    const parsed = parseRecommendationList({
      ...recommendationList,
      items: [recommendationList.items[0], second],
      total: 2,
    })

    expect(parsed.items.map(({ profile }) => profile.id)).toEqual([
      recommendationList.items[0].profile.id,
      second.profile.id,
    ])
  })

  it.each([
    {
      ...recommendationList,
      email: 'private@example.com',
    },
    {
      ...recommendationList,
      total_pages: 2,
    },
    {
      ...recommendationList,
      reference_week_start: '2026-02-31',
    },
    {
      ...recommendationList,
      items: [
        {
          ...recommendationList.items[0],
          explanation: {
            ...recommendationList.items[0].explanation,
            interests: { similarity: 0.75, weight: 35, points: 30 },
          },
        },
      ],
    },
    {
      ...recommendationList,
      items: [
        {
          ...recommendationList.items[0],
          profile: { ...recommendationList.items[0].profile, user_id: 'internal-user-id' },
        },
      ],
    },
    {
      ...recommendationList,
      items: [
        {
          ...recommendationList.items[0],
          profile: {
            ...recommendationList.items[0].profile,
            interests: [
              {
                id: null,
                code: 'must-not-exist-for-custom',
                label: 'Formula 1',
                is_custom: true,
              },
            ],
          },
        },
      ],
    },
  ])('rejects unexpected, private or inconsistent response data', (payload) => {
    expect(() => parseRecommendationList(payload)).toThrowError(
      expect.objectContaining({ code: 'invalidResponse' } satisfies Partial<ApiError>),
    )
  })
})
