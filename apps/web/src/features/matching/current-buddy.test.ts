import { describe, expect, it } from 'vitest'

import {
  conversationIdFromBuddyLocation,
  currentBuddiesDestination,
  parseCurrentBuddyList,
} from '@/features/matching/current-buddy'
import { ApiError } from '@/lib/api'
import { currentBuddyList } from '@/test/current-buddies'

describe('BUDDY-003 Current Buddy contracts', () => {
  it('parses a strict privacy-safe paginated response', () => {
    expect(parseCurrentBuddyList(currentBuddyList)).toEqual(currentBuddyList)
  })

  it.each(['email', 'user_id', 'normalized_key', 'storage_path', 'score_breakdown'])(
    'rejects private or internal Buddy field %s',
    (privateField) => {
      const payload = structuredClone(currentBuddyList) as Record<string, unknown>
      const buddy = (payload.items as Array<Record<string, unknown>>)[0].buddy as Record<
        string,
        unknown
      >
      buddy[privateField] = 'private-value'
      expect(() => parseCurrentBuddyList(payload)).toThrow(ApiError)
    },
  )

  it('rejects duplicate opaque match or conversation identities and inconsistent pages', () => {
    const duplicate = {
      ...currentBuddyList,
      items: [...currentBuddyList.items, structuredClone(currentBuddyList.items[0])],
      total: 2,
    }
    expect(() => parseCurrentBuddyList(duplicate)).toThrow(ApiError)

    expect(() => parseCurrentBuddyList({ ...currentBuddyList, total: 21, total_pages: 1 })).toThrow(
      ApiError,
    )
  })

  it('canonicalizes only the approved Buddy conversation location into the matching section', () => {
    const conversationId = currentBuddyList.items[0].conversation_id
    const location = {
      pathname: '/user/buddy',
      search: `?conversation=${conversationId}`,
      hash: '',
    }
    expect(conversationIdFromBuddyLocation(location)).toBe(conversationId)
    expect(currentBuddiesDestination(conversationId)).toBe(
      `/user/matching?conversation=${conversationId}#current-buddies`,
    )
    expect(currentBuddiesDestination(null)).toBe('/user/matching#current-buddies')
  })

  it.each([
    '?conversation=not-a-uuid',
    `?conversation=${currentBuddyList.items[0].conversation_id}&next=https://attacker.example`,
    `?conversation=${currentBuddyList.items[0].conversation_id}&conversation=${currentBuddyList.items[0].conversation_id}`,
  ])('fails closed for unsafe or malformed Buddy search %s', (search) => {
    expect(
      conversationIdFromBuddyLocation({ pathname: '/user/buddy', search, hash: '' }),
    ).toBeNull()
  })
})
