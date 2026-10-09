import type {
  AdminEvent,
  EventDraftPayload,
  EventVisibility,
} from '@/features/admin-events/admin-events'

const MAX_EVENT_COVER_BYTES = 5 * 1024 * 1024
const EVENT_COVER_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

interface EventFormValues {
  titleEn: string
  titleDe: string
  descriptionEn: string
  descriptionDe: string
  startDate: string
  endDate: string
  timezone: string
  locationEn: string
  locationDe: string
  category: string
  organizer: string
  registrationUrl: string
  visibility: EventVisibility
  registrationEnabled: boolean
  maxParticipants: string
  registrationDeadline: string
  altEn: string
  altDe: string
}

type EventFormErrors = Partial<Record<keyof EventFormValues | 'cover', string>>

const emptyEventFormValues: EventFormValues = {
  titleEn: '',
  titleDe: '',
  descriptionEn: '',
  descriptionDe: '',
  startDate: '',
  endDate: '',
  timezone: 'Asia/Ho_Chi_Minh',
  locationEn: '',
  locationDe: '',
  category: '',
  organizer: '',
  registrationUrl: '',
  visibility: 'MEMBERS',
  registrationEnabled: false,
  maxParticipants: '',
  registrationDeadline: '',
  altEn: '',
  altDe: '',
}

function textOrNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed || null
}

function localParts(value: string): number[] | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value)
  if (!match) return null
  return match.slice(1).map(Number)
}

function zoneParts(instant: Date, timezone: string): number[] {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(instant)
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    Number(parts.find((part) => part.type === type)?.value)
  return [value('year'), value('month'), value('day'), value('hour'), value('minute')]
}

function zonedLocalToIso(value: string, timezone: string): string | null {
  const desired = localParts(value)
  if (!desired) return null
  try {
    const desiredUtc = Date.UTC(desired[0], desired[1] - 1, desired[2], desired[3], desired[4])
    let timestamp = desiredUtc
    for (let pass = 0; pass < 3; pass += 1) {
      const observed = zoneParts(new Date(timestamp), timezone)
      const observedUtc = Date.UTC(
        observed[0],
        observed[1] - 1,
        observed[2],
        observed[3],
        observed[4],
      )
      timestamp += desiredUtc - observedUtc
    }
    const instant = new Date(timestamp)
    if (zoneParts(instant, timezone).join(':') !== desired.join(':')) return null
    return instant.toISOString()
  } catch {
    return null
  }
}

function isoToZonedLocal(value: string | null, timezone: string): string {
  if (!value) return ''
  try {
    const [year, month, day, hour, minute] = zoneParts(new Date(value), timezone)
    const pad = (part: number) => String(part).padStart(2, '0')
    return `${year}-${pad(month)}-${pad(day)}T${pad(hour)}:${pad(minute)}`
  } catch {
    return ''
  }
}

function eventToFormValues(event: AdminEvent): EventFormValues {
  return {
    ...emptyEventFormValues,
    titleEn: event.title_en ?? '',
    titleDe: event.title_de ?? '',
    descriptionEn: event.description_en ?? '',
    descriptionDe: event.description_de ?? '',
    startDate: isoToZonedLocal(event.start_date, event.timezone),
    endDate: isoToZonedLocal(event.end_date, event.timezone),
    timezone: event.timezone,
    locationEn: event.location_en ?? '',
    locationDe: event.location_de ?? '',
    category: event.category ?? '',
    organizer: event.organizer ?? '',
    registrationUrl: event.registration_url ?? '',
    visibility: event.visibility,
    registrationEnabled: event.registration_enabled,
    maxParticipants: event.max_participants ? String(event.max_participants) : '',
    registrationDeadline: isoToZonedLocal(event.registration_deadline, event.timezone),
  }
}

function validateEventCover(file: File | null): 'type' | 'size' | null {
  if (!file) return null
  if (!EVENT_COVER_TYPES.has(file.type)) return 'type'
  if (file.size < 1 || file.size > MAX_EVENT_COVER_BYTES) return 'size'
  return null
}

function validateEventForm(
  values: EventFormValues,
  file: File | null,
  message: (key: string) => string,
): EventFormErrors {
  const errors: EventFormErrors = {}
  const limits: [keyof EventFormValues, number][] = [
    ['titleEn', 120],
    ['titleDe', 120],
    ['descriptionEn', 10_000],
    ['descriptionDe', 10_000],
    ['locationEn', 200],
    ['locationDe', 200],
    ['category', 80],
    ['organizer', 200],
  ]
  for (const [field, maximum] of limits) {
    if (String(values[field]).trim().length > maximum) errors[field] = message('maximum')
  }
  if (!values.timezone.trim() || !zonedLocalToIso('2026-01-15T12:00', values.timezone.trim())) {
    errors.timezone = message('timezone')
  }
  const start = values.startDate ? zonedLocalToIso(values.startDate, values.timezone.trim()) : null
  const end = values.endDate ? zonedLocalToIso(values.endDate, values.timezone.trim()) : null
  const deadline = values.registrationDeadline
    ? zonedLocalToIso(values.registrationDeadline, values.timezone.trim())
    : null
  if (values.startDate && !start) errors.startDate = message('datetime')
  if (values.endDate && !end) errors.endDate = message('datetime')
  if (values.registrationDeadline && !deadline) {
    errors.registrationDeadline = message('datetime')
  }
  if (start && end && new Date(end) <= new Date(start)) errors.endDate = message('endAfterStart')
  if (start && deadline && new Date(deadline) > new Date(start)) {
    errors.registrationDeadline = message('deadlineBeforeStart')
  }
  if (values.registrationUrl.trim()) {
    try {
      if (new URL(values.registrationUrl.trim()).protocol !== 'https:') throw new Error()
    } catch {
      errors.registrationUrl = message('https')
    }
  }
  if (
    values.maxParticipants &&
    (!/^\d+$/.test(values.maxParticipants) || Number(values.maxParticipants) < 1)
  ) {
    errors.maxParticipants = message('positiveInteger')
  }
  const fileError = validateEventCover(file)
  if (fileError) errors.cover = message(fileError === 'type' ? 'coverType' : 'coverSize')
  if (file && !values.altEn.trim()) errors.altEn = message('required')
  if (file && !values.altDe.trim()) errors.altDe = message('required')
  if (values.altEn.trim().length > 200) errors.altEn = message('maximum')
  if (values.altDe.trim().length > 200) errors.altDe = message('maximum')
  return errors
}

function eventFormPayload(values: EventFormValues): EventDraftPayload {
  return {
    title_en: textOrNull(values.titleEn),
    title_de: textOrNull(values.titleDe),
    description_en: textOrNull(values.descriptionEn),
    description_de: textOrNull(values.descriptionDe),
    start_date: values.startDate ? zonedLocalToIso(values.startDate, values.timezone.trim()) : null,
    end_date: values.endDate ? zonedLocalToIso(values.endDate, values.timezone.trim()) : null,
    timezone: values.timezone.trim(),
    location_en: textOrNull(values.locationEn),
    location_de: textOrNull(values.locationDe),
    category: textOrNull(values.category),
    organizer: textOrNull(values.organizer),
    registration_url: textOrNull(values.registrationUrl),
    visibility: values.visibility,
    registration_enabled: values.registrationEnabled,
    max_participants: values.maxParticipants ? Number(values.maxParticipants) : null,
    registration_deadline: values.registrationDeadline
      ? zonedLocalToIso(values.registrationDeadline, values.timezone.trim())
      : null,
  }
}

export {
  EVENT_COVER_TYPES,
  MAX_EVENT_COVER_BYTES,
  emptyEventFormValues,
  eventFormPayload,
  eventToFormValues,
  isoToZonedLocal,
  validateEventCover,
  validateEventForm,
  zonedLocalToIso,
}
export type { EventFormErrors, EventFormValues }
