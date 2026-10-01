import { describe, expect, it } from 'vitest'

import {
  canonicalEmailReturnTo,
  emailLoginPathForLocation,
  emailReturnToFromLoginSearch,
} from '@/features/auth/email-deep-link'

const INVITATION_ID = '11111111-1111-4111-8111-111111111111'
const CONVERSATION_ID = '44444444-4444-4444-8444-444444444444'

describe('INV-009 email deep-link allowlist', () => {
  it.each([
    [`/user/matching?invitation=${INVITATION_ID}`],
    [`/user/buddy?conversation=${CONVERSATION_ID}`],
  ])('accepts and canonicalizes the approved internal destination %s', (destination) => {
    expect(canonicalEmailReturnTo(destination)).toBe(destination)
    expect(emailReturnToFromLoginSearch(`?returnTo=${encodeURIComponent(destination)}`)).toBe(
      destination,
    )
  })

  it.each([
    'https://attacker.example/user/buddy?conversation=' + CONVERSATION_ID,
    '//attacker.example/user/buddy?conversation=' + CONVERSATION_ID,
    '/\\attacker.example/user/buddy?conversation=' + CONVERSATION_ID,
    '/admin/users?conversation=' + CONVERSATION_ID,
    '/user/buddy?conversation=not-a-uuid',
    `/user/buddy?conversation=${CONVERSATION_ID}&next=https://attacker.example`,
    `/user/buddy?conversation=${CONVERSATION_ID}#private`,
    `/user/buddy/../matching?invitation=${INVITATION_ID}`,
    '/user/buddy?conversation=AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA',
  ])('rejects non-canonical or non-allowlisted returnTo %s', (destination) => {
    expect(canonicalEmailReturnTo(destination)).toBeNull()
  })

  it('rejects duplicate and privilege-bearing login parameters', () => {
    const destination = `/user/buddy?conversation=${CONVERSATION_ID}`
    expect(
      emailReturnToFromLoginSearch(
        `?returnTo=${encodeURIComponent(destination)}&returnTo=${encodeURIComponent(destination)}`,
      ),
    ).toBeNull()
    expect(
      emailReturnToFromLoginSearch(`?returnTo=${encodeURIComponent(destination)}&role=ADMIN`),
    ).toBeNull()
  })

  it('builds login returnTo only for approved email destinations', () => {
    const destination = `/user/buddy?conversation=${CONVERSATION_ID}`
    expect(
      emailLoginPathForLocation({
        pathname: '/user/buddy',
        search: `?conversation=${CONVERSATION_ID}`,
        hash: '',
      }),
    ).toBe(`/login?returnTo=${encodeURIComponent(destination)}`)
    expect(
      emailLoginPathForLocation({ pathname: '/user/profile', search: '', hash: '' }),
    ).toBeNull()
  })
})
