import { CalendarClock, Languages } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Typography } from '@/components/ui/typography'
import type {
  CompatibilityExplanation,
  CompatibilitySignal,
  MatchingAvailability,
  MatchingLanguage,
  MatchingPreference,
} from '@/features/matching/recommendation'
import type { CatalogLocale } from '@/features/profile/profile-catalog'

const compatibilitySignals = [
  'interests',
  'activities',
  'availability',
  'languages',
  'major',
] as const satisfies readonly (keyof CompatibilityExplanation)[]

function formatNumber(value: number, locale: CatalogLocale): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value)
}

function minuteLabel(minutes: number): string {
  if (minutes === 1440) return '24:00'
  return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`
}

function PreferenceList({
  label,
  values,
}: {
  label: string
  values: readonly MatchingPreference[]
}) {
  const { t } = useTranslation()

  return (
    <div className="space-y-2">
      <Typography variant="small" className="font-semibold">
        {label}
      </Typography>
      {values.length > 0 ? (
        <ul aria-label={label} className="flex flex-wrap gap-2">
          {values.map((value) => (
            <li
              key={value.id ?? `custom:${value.label}`}
              className="max-w-full break-words rounded-full border border-border bg-background px-3 py-1 text-xs font-medium"
            >
              {value.label}
              {value.is_custom ? (
                <span className="sr-only"> {t('recommendedBuddies.customPreference')}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <Typography variant="muted">{t('recommendedBuddies.noneShared')}</Typography>
      )}
    </div>
  )
}

function LanguageList({ values }: { values: readonly MatchingLanguage[] }) {
  const { t } = useTranslation()
  const label = t('recommendedBuddies.languages')

  return (
    <div className="space-y-2">
      <Typography variant="small" className="flex items-center gap-2 font-semibold">
        <Languages aria-hidden="true" className="size-4" />
        {label}
      </Typography>
      {values.length > 0 ? (
        <ul aria-label={label} className="flex flex-wrap gap-2">
          {values.map((value) => (
            <li
              key={value.code ?? `custom:${value.label}`}
              className="max-w-full break-words rounded-full border border-border bg-background px-3 py-1 text-xs font-medium"
            >
              {t('recommendedBuddies.languageValue', {
                language: value.label,
                proficiency: t(`recommendedBuddies.proficiencies.${value.proficiency}`),
              })}
              {value.is_custom ? (
                <span className="sr-only"> {t('recommendedBuddies.customPreference')}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <Typography variant="muted">{t('recommendedBuddies.noneShared')}</Typography>
      )}
    </div>
  )
}

function Availability({ availability }: { availability: MatchingAvailability | null }) {
  const { t } = useTranslation()

  return (
    <div className="space-y-2">
      <Typography variant="small" className="flex items-center gap-2 font-semibold">
        <CalendarClock aria-hidden="true" className="size-4" />
        {t('recommendedBuddies.availability')}
      </Typography>
      {!availability || availability.slots.length === 0 ? (
        <Typography variant="muted">{t('recommendedBuddies.noAvailability')}</Typography>
      ) : (
        <div className="space-y-2">
          <Typography variant="muted" className="break-all">
            {t('recommendedBuddies.timezone', { timezone: availability.timezone })}
          </Typography>
          <ul
            className="grid gap-1 text-sm sm:grid-cols-2"
            aria-label={t('recommendedBuddies.availability')}
          >
            {availability.slots.map((slot, index) => (
              <li key={`${slot.weekday}:${slot.start_minute}:${slot.end_minute}:${index}`}>
                {t('recommendedBuddies.availabilityValue', {
                  day: t(`recommendedBuddies.weekdays.${slot.weekday}`),
                  start: minuteLabel(slot.start_minute),
                  end: minuteLabel(slot.end_minute),
                })}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function CompatibilityRow({
  name,
  signal,
  locale,
}: {
  name: keyof CompatibilityExplanation
  signal: CompatibilitySignal
  locale: CatalogLocale
}) {
  const { t } = useTranslation()
  const label = t(`recommendedBuddies.signals.${name}`)

  return (
    <li className="space-y-1.5">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span>{label}</span>
        <span className="whitespace-nowrap font-semibold">
          {t('recommendedBuddies.signalDetails', {
            similarity: formatNumber(signal.similarity * 100, locale),
            points: formatNumber(signal.points, locale),
            weight: signal.weight,
          })}
        </span>
      </div>
      <progress
        aria-label={t('recommendedBuddies.signalProgress', { signal: label })}
        className="h-2 w-full accent-vgu-orange"
        max={signal.weight || 1}
        value={signal.points}
      />
    </li>
  )
}

function MatchingProfileDetails({
  profile,
}: {
  profile: {
    interests: readonly MatchingPreference[]
    activities: readonly MatchingPreference[]
    languages: readonly MatchingLanguage[]
    availability: MatchingAvailability | null
  }
}) {
  const { t } = useTranslation()
  return (
    <section className="space-y-5" aria-label={t('recommendedBuddies.profileInformation')}>
      <PreferenceList label={t('recommendedBuddies.interests')} values={profile.interests} />
      <PreferenceList label={t('recommendedBuddies.activities')} values={profile.activities} />
      <LanguageList values={profile.languages} />
      <Availability availability={profile.availability} />
    </section>
  )
}

function CompatibilityDetails({
  explanation,
  locale,
  headingId,
}: {
  explanation: CompatibilityExplanation
  locale: CatalogLocale
  headingId: string
}) {
  const { t } = useTranslation()
  return (
    <section
      className="rounded-2xl border border-border/70 bg-muted/35 p-4"
      aria-labelledby={headingId}
    >
      <Typography as="h3" variant="h4" id={headingId}>
        {t('recommendedBuddies.compatibilityBreakdown')}
      </Typography>
      <Typography variant="muted" className="mt-1">
        {t('recommendedBuddies.compatibilityDescription')}
      </Typography>
      <ul className="mt-4 space-y-3">
        {compatibilitySignals.map((signal) => (
          <CompatibilityRow
            key={signal}
            name={signal}
            signal={explanation[signal]}
            locale={locale}
          />
        ))}
      </ul>
    </section>
  )
}

export { CompatibilityDetails, MatchingProfileDetails }
