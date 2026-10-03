import { describe, expect, it } from 'vitest'

import { resolveDynamicEventsLaunchEnabled } from '@/config/launch-scope'

describe('dynamic Event release launch scope', () => {
  it('keeps future dynamic Event placeholders available in development by default', () => {
    expect(resolveDynamicEventsLaunchEnabled({ development: true })).toBe(true)
  })

  it('excludes future API-backed Event surfaces from production by default', () => {
    expect(resolveDynamicEventsLaunchEnabled({ development: false })).toBe(false)
  })

  it('requires an exact explicit opt-in to expose dynamic Events in production', () => {
    expect(resolveDynamicEventsLaunchEnabled({ development: false, eventsFlag: 'true' })).toBe(true)
    expect(resolveDynamicEventsLaunchEnabled({ development: false, eventsFlag: 'TRUE' })).toBe(
      false,
    )
  })

  it('supports an explicit local exclusion of dynamic surfaces for release-like checks', () => {
    expect(resolveDynamicEventsLaunchEnabled({ development: true, eventsFlag: 'false' })).toBe(
      false,
    )
  })
})
