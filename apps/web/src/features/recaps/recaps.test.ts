import { describe, expect, it } from 'vitest'
import { relatedEventDate } from './recaps'
describe('Related Event date prefilling', () => {
  it('uses the canonical Event timezone across a UTC day boundary', () => {
    expect(relatedEventDate('2026-11-03T18:00:00Z', 'Asia/Ho_Chi_Minh')).toBe('2026-11-04')
  })
  it('retains an absent optional Event date', () => {
    expect(relatedEventDate(null, 'Asia/Ho_Chi_Minh')).toBeNull()
  })
})
