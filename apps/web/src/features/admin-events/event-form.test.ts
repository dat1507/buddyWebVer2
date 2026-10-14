import { describe, expect, it } from 'vitest'

import {
  emptyEventFormValues,
  eventFormPayload,
  isoToZonedLocal,
  validateEventCover,
  validateEventForm,
  zonedLocalToIso,
} from '@/features/admin-events/event-form'

describe('ADMIN-007/008 Event form boundaries', () => {
  it('defaults new drafts to the public audience while preserving explicit member-only edits', () => {
    expect(emptyEventFormValues.visibility).toBe('PUBLIC')
    expect(eventFormPayload({ ...emptyEventFormValues, visibility: 'MEMBERS' }).visibility).toBe(
      'MEMBERS',
    )
  })

  it('converts local Event wall time through the selected IANA timezone', () => {
    expect(zonedLocalToIso('2026-10-10T15:00', 'Asia/Ho_Chi_Minh')).toBe('2026-10-10T08:00:00.000Z')
    expect(isoToZonedLocal('2026-10-10T08:00:00Z', 'Asia/Ho_Chi_Minh')).toBe('2026-10-10T15:00')
    expect(zonedLocalToIso('2026-03-29T02:30', 'Europe/Berlin')).toBeNull()
    expect(zonedLocalToIso('2026-10-10T15:00', 'Not/A_Zone')).toBeNull()
  })

  it('trims draft payloads and preserves explicit audience and registration controls', () => {
    expect(
      eventFormPayload({
        ...emptyEventFormValues,
        titleEn: '  Buddy Day  ',
        startDate: '2026-10-10T15:00',
        endDate: '2026-10-10T17:00',
        visibility: 'PUBLIC',
        registrationEnabled: true,
        maxParticipants: '100',
      }),
    ).toMatchObject({
      title_en: 'Buddy Day',
      title_de: null,
      start_date: '2026-10-10T08:00:00.000Z',
      end_date: '2026-10-10T10:00:00.000Z',
      visibility: 'PUBLIC',
      registration_enabled: true,
      max_participants: 100,
    })
  })

  it('rejects invalid schedule, URL, cover type/size, and missing alt text', () => {
    const message = (key: string) => key
    const invalidFile = new File(['svg'], 'poster.svg', { type: 'image/svg+xml' })
    const errors = validateEventForm(
      {
        ...emptyEventFormValues,
        startDate: '2026-10-10T17:00',
        endDate: '2026-10-10T15:00',
        registrationDeadline: '2026-10-10T18:00',
        registrationUrl: 'http://unsafe.example',
        category: 'x'.repeat(500),
        organizer: 'x'.repeat(500),
        maxParticipants: '0',
      },
      invalidFile,
      message,
    )

    expect(errors).toMatchObject({
      endDate: 'endAfterStart',
      registrationDeadline: 'deadlineBeforeStart',
      registrationUrl: 'https',
      cover: 'coverType',
      altEn: 'required',
      altDe: 'required',
    })
    expect(errors.category).toBeUndefined()
    expect(errors.organizer).toBeUndefined()
    expect(errors.maxParticipants).toBeUndefined()
    expect(validateEventCover(new File([], 'empty.png', { type: 'image/png' }))).toBe('size')
  })
})
