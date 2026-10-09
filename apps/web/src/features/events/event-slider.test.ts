import { describe, expect, it } from 'vitest'

import { parsePublicEventSliders } from '@/features/events/event-slider'

const validPayload = {
  id: '11111111-1111-4111-8111-111111111111',
  title: 'Welcome Day',
  description: null,
  image_url: 'https://cdn.example.com/welcome.webp',
  image_alt: 'Students at Welcome Day',
  event_start_at: '2026-10-01T08:00:00+07:00',
  event_end_at: null,
  location: 'VGU campus',
  cta: { label: 'Learn more', href: '/events/11111111-1111-4111-8111-111111111111' },
  sort_order: 0,
}

describe('parsePublicEventSliders', () => {
  it('maps validated API data to the frontend model', () => {
    expect(parsePublicEventSliders([validPayload])).toEqual([
      expect.objectContaining({
        imageUrl: validPayload.image_url,
        eventStartAt: validPayload.event_start_at,
        sortOrder: 0,
      }),
    ])
  })

  it('rejects insecure production image URLs', () => {
    expect(() =>
      parsePublicEventSliders([
        { ...validPayload, image_url: 'http://cdn.example.com/welcome.webp' },
      ]),
    ).toThrow()
  })

  it.each([
    '//evil.example/events/11111111-1111-4111-8111-111111111111',
    '/\\evil.example/events/11111111-1111-4111-8111-111111111111',
    '/events/not-a-uuid',
    'https://evil.example/events/11111111-1111-4111-8111-111111111111',
  ])('rejects a non-canonical internal detail target: %s', (href) => {
    expect(() =>
      parsePublicEventSliders([{ ...validPayload, cta: { label: 'Learn more', href } }]),
    ).toThrow()
  })

  it('requires every live slide to link to its Event detail', () => {
    expect(() => parsePublicEventSliders([{ ...validPayload, cta: null }])).toThrow()
  })
})
