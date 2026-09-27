import { afterEach, describe, expect, it, vi } from 'vitest'

import { sessionClient } from '@/features/auth/session-client'
import { matchingClient } from '@/features/matching/matching-client'
import { recommendationList } from '@/test/recommendations'

describe('REC-004 matching client', () => {
  afterEach(() => vi.restoreAllMocks())

  it('calls only the read-only recommendation endpoint with bounded paging and locale', async () => {
    const authenticatedJson = vi
      .spyOn(sessionClient, 'authenticatedJson')
      .mockResolvedValue(recommendationList)
    const controller = new AbortController()

    await expect(
      matchingClient.readRecommendations({
        locale: 'de',
        page: 2,
        pageSize: 20,
        signal: controller.signal,
      }),
    ).resolves.toEqual(recommendationList)

    expect(authenticatedJson).toHaveBeenCalledWith(
      '/matching/recommendations?locale=de&page=2&page_size=20',
      { signal: controller.signal },
    )
    expect(authenticatedJson.mock.calls[0][1]).not.toHaveProperty('method')
  })
})
