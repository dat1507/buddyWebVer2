import { describe, expect, it } from 'vitest'

import { resolveEventsLaunchEnabled } from '@/config/launch-scope'

describe('release launch scope', () => {
  it('keeps development fixtures available when no override is supplied', () => {
    expect(resolveEventsLaunchEnabled({ development: true })).toBe(true)
  })

  it('excludes the incomplete Event track from production by default', () => {
    expect(resolveEventsLaunchEnabled({ development: false })).toBe(false)
  })

  it('requires an exact explicit opt-in to expose Events in production', () => {
    expect(resolveEventsLaunchEnabled({ development: false, eventsFlag: 'true' })).toBe(true)
    expect(resolveEventsLaunchEnabled({ development: false, eventsFlag: 'TRUE' })).toBe(false)
  })

  it('supports an explicit local exclusion for release-like checks', () => {
    expect(resolveEventsLaunchEnabled({ development: true, eventsFlag: 'false' })).toBe(false)
  })
})
