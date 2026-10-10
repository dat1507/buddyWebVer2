import { describe, expect, it } from 'vitest'

import { resolveEventFeatureFlags } from '@/config/launch-scope'

describe('Event feature flags', () => {
  it.each([
    [undefined, undefined, false, false],
    ['false', 'false', false, false],
    ['true', 'false', true, false],
    ['false', 'true', false, true],
    ['true', 'true', true, true],
  ])(
    'resolves admin=%s and public=%s independently',
    (adminEventsFlag, publicEventsFlag, adminEventsEnabled, publicEventsEnabled) => {
      expect(resolveEventFeatureFlags({ adminEventsFlag, publicEventsFlag })).toEqual({
        adminEventsEnabled,
        publicEventsEnabled,
      })
    },
  )

  it.each(['TRUE', '1', ' true ', '', 'yes'])('keeps invalid value %j off', (invalidFlag) => {
    expect(
      resolveEventFeatureFlags({
        adminEventsFlag: invalidFlag,
        publicEventsFlag: invalidFlag,
      }),
    ).toEqual({ adminEventsEnabled: false, publicEventsEnabled: false })
  })

  it('ignores the retired shared flag even when it is true', () => {
    expect(resolveEventFeatureFlags({ legacyEventsFlag: 'true' })).toEqual({
      adminEventsEnabled: false,
      publicEventsEnabled: false,
    })
  })
})
