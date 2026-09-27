import { useId, useRef, useState, type FormEvent } from 'react'
import { CalendarClock, CheckCircle2, LoaderCircle, Plus, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import {
  MAX_ACTIVITIES,
  type CatalogLocale,
  type CustomPreferenceSelection,
  type ProfilePreferenceSnapshot,
} from '@/features/profile/profile-catalog'
import type { ProfileMissingField } from '@/features/profile/profile-completion'
import type { PreferenceTagMessages } from '@/features/profile/preference-tag-input'
import { PreferenceTagInput } from '@/features/profile/preference-tag-input'
import type { ProfileFormMode, ReloadOwnProfile } from '@/features/profile/profile-form'
import type {
  OnboardingPreferencesUpdate,
  OwnProfile,
  WeeklyAvailabilitySlot,
} from '@/features/profile/profile'
import { useActivityCatalog } from '@/features/profile/queries/use-profile-catalogs'
import {
  useOwnProfile,
  useProfileCompletion,
  useProfilePreferences,
  useUpdateOwnProfile,
  useUpdateProfilePreferences,
} from '@/features/profile/queries/use-own-profile'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'

const MAX_SLOTS = 100
const HALF_HOUR_MINUTES = Array.from({ length: 49 }, (_, index) => index * 30)

const inputClassName =
  'h-11 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none transition hover:border-foreground/25 focus-visible:border-vgu-orange focus-visible:ring-2 focus-visible:ring-vgu-orange/25 disabled:cursor-not-allowed disabled:opacity-60'

interface AvailabilitySlotDraft extends WeeklyAvailabilitySlot {
  id: number
}

function catalogLocale(language: string | undefined): CatalogLocale {
  return language?.split('-')[0] === 'de' ? 'de' : 'en'
}

function detectedTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  } catch {
    return 'UTC'
  }
}

function minuteLabel(minutes: number): string {
  if (minutes === 1440) return '24:00'
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return `${String(hours).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
}

function timeOptions(current: number, allowDayEnd: boolean): number[] {
  const base = allowDayEnd ? HALF_HOUR_MINUTES : HALF_HOUR_MINUTES.slice(0, -1)
  return base.includes(current) ? base : [...base, current].sort((left, right) => left - right)
}

function missingStep(
  field: ProfileMissingField,
): '/user/onboarding' | '/user/onboarding/interests' {
  return field === 'INTERESTS' || field === 'LANGUAGES'
    ? '/user/onboarding/interests'
    : '/user/onboarding'
}

function OnboardingPreferencesEditor({
  profile,
  preferences,
  mode = 'onboarding',
  onReload,
  reloadPreferences,
}: {
  profile: OwnProfile
  preferences: ProfilePreferenceSnapshot
  mode?: ProfileFormMode
  onReload?: ReloadOwnProfile
  reloadPreferences: () => Promise<ProfilePreferenceSnapshot | undefined>
}) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const locale = catalogLocale(i18n.resolvedLanguage)
  const alternateLocale: CatalogLocale = locale === 'en' ? 'de' : 'en'
  const activities = useActivityCatalog(locale)
  const alternateActivities = useActivityCatalog(alternateLocale)
  const completion = useProfileCompletion()
  const updateProfile = useUpdateOwnProfile()
  const updatePreferences = useUpdateProfilePreferences()
  const timezoneId = useId()
  const initialSlots = profile.availability?.slots ?? []
  const nextSlotId = useRef(initialSlots.length + 1)
  const [availabilityEnabled, setAvailabilityEnabled] = useState(profile.availability !== null)
  const [timezone, setTimezone] = useState(profile.availability?.timezone ?? detectedTimezone())
  const [slots, setSlots] = useState<AvailabilitySlotDraft[]>(() =>
    initialSlots.map((slot, index) => ({ ...slot, id: index + 1 })),
  )
  const [selectedActivityIds, setSelectedActivityIds] = useState<string[]>(() => [
    ...preferences.activity_ids,
  ])
  const [customActivities, setCustomActivities] = useState<CustomPreferenceSelection[]>(() =>
    preferences.custom_activities.map((selection) => ({ ...selection })),
  )
  const [matchingOptIn, setMatchingOptIn] = useState(profile.matching_opt_in)
  const [formError, setFormError] = useState<string | null>(null)
  const [completionError, setCompletionError] = useState(false)
  const [checkingCompletion, setCheckingCompletion] = useState(false)
  const [missingFields, setMissingFields] = useState<ProfileMissingField[] | null>(null)
  const [reloading, setReloading] = useState(false)

  const clearFeedback = () => {
    setFormError(null)
    setCompletionError(false)
    setMissingFields(null)
    updateProfile.reset()
    updatePreferences.reset()
  }

  const availableActivityIds = new Set(activities.data?.items.map(({ id }) => id) ?? [])
  const unavailableActivityIds = selectedActivityIds.filter((id) => !availableActivityIds.has(id))
  const activityCount = selectedActivityIds.length + customActivities.length
  const activityCollisionLabels = [
    ...(activities.data?.items.map(({ label }) => label) ?? []),
    ...(alternateActivities.data?.items.map(({ label }) => label) ?? []),
  ]
  const isPending = updateProfile.isPending || updatePreferences.isPending || checkingCompletion
  const tagMessages: PreferenceTagMessages = {
    inputLabel: t('preferenceTags.activity.inputLabel'),
    placeholder: t('preferenceTags.activity.placeholder'),
    add: t('preferenceTags.activity.add'),
    customBadge: t('preferenceTags.customBadge'),
    remove: (label) => t('preferenceTags.remove', { label }),
    invalid: t('preferenceTags.invalid'),
    duplicate: t('preferenceTags.duplicate'),
    predefinedCollision: t('preferenceTags.predefinedCollision'),
    limitReached: t('preferenceTags.limitReached'),
    characterCount: (count, maximum) => t('preferenceTags.characterCount', { count, maximum }),
  }

  const addSlot = () => {
    clearFeedback()
    setSlots((current) => [
      ...current,
      { id: nextSlotId.current++, weekday: 1, start_minute: 540, end_minute: 600 },
    ])
  }

  const updateSlot = (
    id: number,
    field: 'weekday' | 'start_minute' | 'end_minute',
    value: number,
  ) => {
    clearFeedback()
    setSlots((current) =>
      current.map((slot) => (slot.id === id ? { ...slot, [field]: value } : slot)),
    )
  }

  const verifyCompletion = async () => {
    setCheckingCompletion(true)
    setCompletionError(false)
    setMissingFields(null)
    const result = await completion.refetch()
    setCheckingCompletion(false)

    if (result.isError || !result.data) {
      setCompletionError(true)
      return
    }
    if (result.data.status === 'COMPLETE' && mode === 'onboarding') {
      navigate('/user/dashboard', { replace: true })
      return
    }
    setMissingFields([...result.data.missing_fields])
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isPending || !activities.data) return
    clearFeedback()

    const normalizedTimezone = timezone.trim()
    if (availabilityEnabled && (!normalizedTimezone || normalizedTimezone.length > 64)) {
      setFormError(t('onboarding.preferences.validation.timezone'))
      return
    }
    if (availabilityEnabled && slots.length === 0) {
      setFormError(t('onboarding.preferences.validation.slotRequired'))
      return
    }
    if (availabilityEnabled && slots.some((slot) => slot.start_minute === slot.end_minute)) {
      setFormError(t('onboarding.preferences.validation.slotLength'))
      return
    }
    if (unavailableActivityIds.length > 0) {
      setFormError(t('onboarding.preferences.validation.unavailableActivities'))
      return
    }

    const update: OnboardingPreferencesUpdate = {
      version: preferences.version,
      availability: availabilityEnabled
        ? {
            timezone: normalizedTimezone,
            slots: slots.map(({ weekday, start_minute, end_minute }) => ({
              weekday,
              start_minute,
              end_minute,
            })),
          }
        : null,
      matching_opt_in: matchingOptIn,
    }

    try {
      const activitiesChanged =
        selectedActivityIds.length !== preferences.activity_ids.length ||
        selectedActivityIds.some((id) => !preferences.activity_ids.includes(id)) ||
        customActivities.length !== preferences.custom_activities.length ||
        customActivities.some(
          ({ label }, index) => preferences.custom_activities[index]?.label !== label,
        )
      let version = preferences.version
      if (activitiesChanged) {
        const savedPreferences = await updatePreferences.mutateAsync({
          version,
          interest_ids: [...preferences.interest_ids],
          custom_interests: preferences.custom_interests.map((selection) => ({ ...selection })),
          languages: preferences.languages.map((selection) => ({ ...selection })),
          custom_languages: preferences.custom_languages.map((selection) => ({ ...selection })),
          activity_ids: selectedActivityIds,
          custom_activities: customActivities,
        })
        version = savedPreferences.version
        setSelectedActivityIds([...savedPreferences.activity_ids])
        setCustomActivities(
          savedPreferences.custom_activities.map((selection) => ({ ...selection })),
        )
      }
      await updateProfile.mutateAsync({ ...update, version })
      await verifyCompletion()
    } catch {
      // The mutation exposes a sanitized error below and preserves every local field for retry.
    }
  }

  const mutationError = updatePreferences.error ?? updateProfile.error
  const saveError =
    mutationError instanceof ApiError && mutationError.code === 'validation'
      ? t('onboarding.preferences.serverValidation')
      : mutationError instanceof ApiError && mutationError.code === 'conflict'
        ? t(mode === 'edit' ? 'profileEdit.conflict' : 'onboarding.preferences.conflict')
        : t('onboarding.preferences.saveError')
  const hasConflict = mutationError instanceof ApiError && mutationError.code === 'conflict'

  const reloadSavedProfile = async () => {
    if (!onReload || reloading) return
    setReloading(true)
    const [refreshedProfile, refreshedPreferences] = await Promise.all([
      onReload(),
      reloadPreferences(),
    ])
    setReloading(false)
    if (!refreshedProfile || !refreshedPreferences) return

    const refreshedSlots = refreshedProfile.availability?.slots ?? []
    setAvailabilityEnabled(refreshedProfile.availability !== null)
    setTimezone(refreshedProfile.availability?.timezone ?? detectedTimezone())
    setSlots(refreshedSlots.map((slot, index) => ({ ...slot, id: index + 1 })))
    nextSlotId.current = refreshedSlots.length + 1
    setSelectedActivityIds([...refreshedPreferences.activity_ids])
    setCustomActivities(
      refreshedPreferences.custom_activities.map((selection) => ({ ...selection })),
    )
    setMatchingOptIn(refreshedProfile.matching_opt_in)
    setFormError(null)
    setCompletionError(false)
    setMissingFields(null)
    updateProfile.reset()
    updatePreferences.reset()
  }

  const titleId =
    mode === 'edit' ? 'profile-edit-preferences-title' : 'onboarding-preferences-title'

  return (
    <section className="min-w-0 space-y-6 py-6" aria-labelledby={titleId}>
      <header className="space-y-2">
        <Typography
          variant="small"
          className="font-semibold uppercase tracking-[0.18em] text-vgu-orange"
        >
          {t(mode === 'edit' ? 'profileEdit.preferencesEyebrow' : 'onboarding.preferences.step')}
        </Typography>
        <Typography as={mode === 'edit' ? 'h2' : 'h1'} variant="h2" id={titleId}>
          {t(mode === 'edit' ? 'profileEdit.preferencesTitle' : 'onboarding.preferences.title')}
        </Typography>
        <Typography variant="muted" className="max-w-3xl text-base leading-7">
          {t(
            mode === 'edit' ? 'profileEdit.preferencesSubtitle' : 'onboarding.preferences.subtitle',
          )}
        </Typography>
      </header>

      <form className="space-y-6" aria-busy={isPending} onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CalendarClock className="size-5 text-vgu-orange" aria-hidden="true" />
              {t('onboarding.preferences.availabilityTitle')}
            </CardTitle>
            <CardDescription>{t('onboarding.preferences.availabilityDescription')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border p-4">
              <input
                type="checkbox"
                checked={availabilityEnabled}
                disabled={isPending}
                className="mt-1 size-4 shrink-0 accent-vgu-orange focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange"
                onChange={(event) => {
                  clearFeedback()
                  setAvailabilityEnabled(event.target.checked)
                }}
              />
              <span>
                <span className="block text-sm font-semibold">
                  {t('onboarding.preferences.addAvailability')}
                </span>
                <span className="mt-1 block text-sm text-muted-foreground">
                  {t('onboarding.preferences.skipAvailability')}
                </span>
              </span>
            </label>

            {availabilityEnabled ? (
              <div className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor={timezoneId} className="text-sm font-medium">
                    {t('onboarding.preferences.timezoneLabel')}
                  </label>
                  <input
                    id={timezoneId}
                    value={timezone}
                    disabled={isPending}
                    className={inputClassName}
                    aria-describedby={`${timezoneId}-help`}
                    onChange={(event) => {
                      clearFeedback()
                      setTimezone(event.target.value)
                    }}
                  />
                  <p id={`${timezoneId}-help`} className="text-xs text-muted-foreground">
                    {t('onboarding.preferences.timezoneHelp')}
                  </p>
                </div>

                <div className="space-y-3">
                  {slots.map((slot, index) => (
                    <div
                      key={slot.id}
                      className="grid gap-3 rounded-xl border border-border p-4 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end"
                    >
                      <div className="space-y-2">
                        <label
                          htmlFor={`availability-day-${slot.id}`}
                          className="text-sm font-medium"
                        >
                          {t('onboarding.preferences.dayLabel', { number: index + 1 })}
                        </label>
                        <select
                          id={`availability-day-${slot.id}`}
                          value={slot.weekday}
                          disabled={isPending}
                          className={inputClassName}
                          onChange={(event) =>
                            updateSlot(slot.id, 'weekday', Number(event.target.value))
                          }
                        >
                          {Array.from({ length: 7 }, (_, dayIndex) => dayIndex + 1).map(
                            (weekday) => (
                              <option key={weekday} value={weekday}>
                                {t(`onboarding.preferences.weekdays.${weekday}`)}
                              </option>
                            ),
                          )}
                        </select>
                      </div>
                      <div className="space-y-2">
                        <label
                          htmlFor={`availability-start-${slot.id}`}
                          className="text-sm font-medium"
                        >
                          {t('onboarding.preferences.startLabel')}
                        </label>
                        <select
                          id={`availability-start-${slot.id}`}
                          value={slot.start_minute}
                          disabled={isPending}
                          className={inputClassName}
                          onChange={(event) =>
                            updateSlot(slot.id, 'start_minute', Number(event.target.value))
                          }
                        >
                          {timeOptions(slot.start_minute, false).map((minutes) => (
                            <option key={minutes} value={minutes}>
                              {minuteLabel(minutes)}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="space-y-2">
                        <label
                          htmlFor={`availability-end-${slot.id}`}
                          className="text-sm font-medium"
                        >
                          {t('onboarding.preferences.endLabel')}
                        </label>
                        <select
                          id={`availability-end-${slot.id}`}
                          value={slot.end_minute}
                          disabled={isPending}
                          className={inputClassName}
                          onChange={(event) =>
                            updateSlot(slot.id, 'end_minute', Number(event.target.value))
                          }
                        >
                          {timeOptions(slot.end_minute, true).map((minutes) => (
                            <option key={minutes} value={minutes}>
                              {minuteLabel(minutes)}
                            </option>
                          ))}
                        </select>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        disabled={isPending}
                        aria-label={t('onboarding.preferences.removeSlot', { number: index + 1 })}
                        onClick={() => {
                          clearFeedback()
                          setSlots((current) => current.filter(({ id }) => id !== slot.id))
                        }}
                      >
                        <Trash2 aria-hidden="true" />
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    disabled={isPending || slots.length >= MAX_SLOTS}
                    onClick={addSlot}
                  >
                    <Plus aria-hidden="true" />
                    {t('onboarding.preferences.addSlot')}
                  </Button>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('onboarding.preferences.activitiesTitle')}</CardTitle>
            <CardDescription>
              {t('onboarding.preferences.activitiesDescription', { maximum: MAX_ACTIVITIES })}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {activities.isPending ? (
              <div className="flex min-h-24 items-center justify-center gap-3" role="status">
                <LoaderCircle
                  className="size-5 animate-spin motion-reduce:animate-none"
                  aria-hidden="true"
                />
                {t('onboarding.preferences.loadingActivities')}
              </div>
            ) : activities.isError ? (
              <div className="space-y-3 rounded-xl border border-destructive/40 bg-destructive/5 p-4">
                <p className="text-sm text-destructive" role="alert">
                  {t('onboarding.preferences.activitiesError')}
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void activities.refetch()}
                >
                  {t('onboarding.preferences.retry')}
                </Button>
              </div>
            ) : (
              <>
                <p
                  id="preferred-activity-limit"
                  className="text-sm text-muted-foreground"
                  aria-live="polite"
                >
                  {t('onboarding.preferences.activityCount', {
                    count: activityCount,
                    maximum: MAX_ACTIVITIES,
                  })}
                </p>
                {unavailableActivityIds.length > 0 ? (
                  <div className="flex flex-col gap-3 rounded-xl border border-amber-500/50 bg-amber-500/5 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-sm">{t('onboarding.preferences.unavailableActivities')}</p>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        clearFeedback()
                        setSelectedActivityIds((current) =>
                          current.filter((id) => availableActivityIds.has(id)),
                        )
                      }}
                    >
                      {t('onboarding.preferences.removeUnavailableActivities')}
                    </Button>
                  </div>
                ) : null}
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {activities.data?.items.map((activity) => {
                    const checked = selectedActivityIds.includes(activity.id)
                    const disabled = isPending || (!checked && activityCount >= MAX_ACTIVITIES)
                    return (
                      <label
                        key={activity.id}
                        className={cn(
                          'flex cursor-pointer items-center gap-3 rounded-xl border border-border p-3 transition hover:border-vgu-orange/70',
                          checked && 'border-vgu-orange bg-vgu-orange/5',
                          disabled && 'cursor-not-allowed opacity-60',
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={disabled}
                          aria-describedby="preferred-activity-limit"
                          className="size-4 shrink-0 accent-vgu-orange focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange"
                          onChange={() => {
                            clearFeedback()
                            setSelectedActivityIds((current) =>
                              current.includes(activity.id)
                                ? current.filter((id) => id !== activity.id)
                                : [...current, activity.id],
                            )
                          }}
                        />
                        <span className="text-sm font-medium">{activity.label}</span>
                      </label>
                    )
                  })}
                </div>
                <PreferenceTagInput
                  values={customActivities}
                  collisionLabels={activityCollisionLabels}
                  selectedCount={activityCount}
                  maximum={MAX_ACTIVITIES}
                  disabled={isPending}
                  messages={tagMessages}
                  onAdd={(label) => {
                    clearFeedback()
                    setCustomActivities((current) => [...current, { label }])
                  }}
                  onRemove={(index) => {
                    clearFeedback()
                    setCustomActivities((current) =>
                      current.filter((_, itemIndex) => itemIndex !== index),
                    )
                  }}
                />
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('onboarding.preferences.matchingTitle')}</CardTitle>
            <CardDescription>{t('onboarding.preferences.matchingDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            <fieldset className="grid gap-3 sm:grid-cols-2">
              <legend className="sr-only">{t('onboarding.preferences.matchingTitle')}</legend>
              {([true, false] as const).map((value) => (
                <label
                  key={String(value)}
                  className={cn(
                    'flex cursor-pointer items-start gap-3 rounded-xl border border-border p-4 transition hover:border-vgu-orange/70',
                    matchingOptIn === value && 'border-vgu-orange bg-vgu-orange/5',
                  )}
                >
                  <input
                    type="radio"
                    name="matching-opt-in"
                    checked={matchingOptIn === value}
                    disabled={isPending}
                    className="mt-1 size-4 shrink-0 accent-vgu-orange focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange"
                    onChange={() => {
                      clearFeedback()
                      setMatchingOptIn(value)
                    }}
                  />
                  <span>
                    <span className="block text-sm font-semibold">
                      {t(
                        value
                          ? 'onboarding.preferences.optInLabel'
                          : 'onboarding.preferences.optOutLabel',
                      )}
                    </span>
                    <span className="mt-1 block text-sm text-muted-foreground">
                      {t(
                        value
                          ? 'onboarding.preferences.optInHelp'
                          : 'onboarding.preferences.optOutHelp',
                      )}
                    </span>
                  </span>
                </label>
              ))}
            </fieldset>
          </CardContent>
        </Card>

        {formError ? (
          <p
            className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
            role="alert"
          >
            {formError}
          </p>
        ) : updateProfile.isError || updatePreferences.isError ? (
          <div className="space-y-3 rounded-xl border border-destructive/40 bg-destructive/5 p-4">
            <p className="text-sm text-destructive" role="alert">
              {saveError}
            </p>
            {hasConflict && onReload ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={reloading}
                onClick={() => void reloadSavedProfile()}
              >
                {t(reloading ? 'profileEdit.reloading' : 'profileEdit.reloadSaved')}
              </Button>
            ) : null}
          </div>
        ) : null}

        {completionError ? (
          <div className="space-y-3 rounded-xl border border-destructive/40 bg-destructive/5 p-4">
            <p className="text-sm text-destructive" role="alert">
              {t('onboarding.preferences.completionError')}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isPending}
              onClick={() => void verifyCompletion()}
            >
              {t('onboarding.preferences.retryCompletion')}
            </Button>
          </div>
        ) : null}

        {missingFields && missingFields.length > 0 ? (
          <div className="space-y-3 rounded-xl border border-amber-500/50 bg-amber-500/5 p-4">
            <p className="font-semibold" role="status">
              {t('onboarding.preferences.incompleteTitle')}
            </p>
            <p className="text-sm text-muted-foreground">
              {t('onboarding.preferences.incompleteDescription')}
            </p>
            <ul className="space-y-2">
              {missingFields.map((field) => (
                <li key={field}>
                  {mode === 'edit' ? (
                    <span className="text-sm font-semibold">
                      {t(`onboarding.preferences.missingFields.${field}`)}
                    </span>
                  ) : (
                    <Link
                      className="text-sm font-semibold text-vgu-orange underline-offset-4 hover:underline"
                      to={missingStep(field)}
                    >
                      {t(`onboarding.preferences.missingFields.${field}`)} ·{' '}
                      {t(
                        missingStep(field) === '/user/onboarding'
                          ? 'onboarding.preferences.reviewStep1'
                          : 'onboarding.preferences.reviewStep2',
                      )}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="flex flex-col-reverse gap-3 rounded-2xl border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-h-6" aria-live="polite">
            {updateProfile.isSuccess && checkingCompletion ? (
              <p className="flex items-center gap-2 text-sm font-medium">
                <LoaderCircle
                  className="size-4 animate-spin motion-reduce:animate-none"
                  aria-hidden="true"
                />
                {t('onboarding.preferences.checkingCompletion')}
              </p>
            ) : updateProfile.isSuccess && (completionError || missingFields !== null) ? (
              <p className="flex items-center gap-2 text-sm font-medium text-emerald-600">
                <CheckCircle2 className="size-4" aria-hidden="true" />
                {t('onboarding.preferences.saved')}
              </p>
            ) : null}
          </div>
          <Button type="submit" disabled={isPending || !activities.data} className="sm:min-w-48">
            {updateProfile.isPending || updatePreferences.isPending
              ? t('onboarding.preferences.saving')
              : checkingCompletion
                ? t('onboarding.preferences.checking')
                : t(
                    mode === 'edit'
                      ? 'profileEdit.savePreferences'
                      : 'onboarding.preferences.finish',
                  )}
          </Button>
        </div>
      </form>
    </section>
  )
}

function OnboardingPreferencesForm({
  profile,
  mode = 'onboarding',
  onReload,
}: {
  profile: OwnProfile
  mode?: ProfileFormMode
  onReload?: ReloadOwnProfile
}) {
  const { t } = useTranslation()
  const preferences = useProfilePreferences()

  if (preferences.isPending) {
    return (
      <section className="flex min-h-40 items-center justify-center gap-3 py-6" aria-busy="true">
        <LoaderCircle
          className="size-5 animate-spin motion-reduce:animate-none"
          aria-hidden="true"
        />
        <span>{t('onboarding.preferences.loadingPreferenceSelections')}</span>
      </section>
    )
  }

  if (preferences.isError) {
    return (
      <section className="py-6">
        <Card className="mx-auto max-w-2xl">
          <CardHeader>
            <CardTitle>{t('onboarding.preferences.preferenceSelectionsErrorTitle')}</CardTitle>
            <CardDescription role="alert">
              {t('onboarding.preferences.preferenceSelectionsError')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" onClick={() => void preferences.refetch()}>
              {t('onboarding.preferences.retry')}
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }

  const reloadPreferences = async () => {
    const result = await preferences.refetch()
    return result.isError ? undefined : result.data
  }

  return (
    <OnboardingPreferencesEditor
      key={profile.id}
      profile={profile}
      preferences={preferences.data}
      mode={mode}
      onReload={onReload}
      reloadPreferences={reloadPreferences}
    />
  )
}

function OnboardingPreferencesPage() {
  const { t } = useTranslation()
  const profile = useOwnProfile()

  if (profile.isPending) {
    return (
      <section className="flex min-h-72 items-center justify-center gap-3 py-6" aria-busy="true">
        <LoaderCircle
          className="size-5 animate-spin motion-reduce:animate-none"
          aria-hidden="true"
        />
        <span>{t('onboarding.preferences.loadingProfile')}</span>
      </section>
    )
  }

  if (profile.isError) {
    return (
      <section className="py-6" aria-labelledby="onboarding-preferences-load-title">
        <Card className="mx-auto max-w-2xl">
          <CardHeader>
            <CardTitle id="onboarding-preferences-load-title">
              {t('onboarding.preferences.profileErrorTitle')}
            </CardTitle>
            <CardDescription role="alert">
              {t('onboarding.preferences.profileError')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" onClick={() => void profile.refetch()}>
              {t('onboarding.preferences.retry')}
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }

  return <OnboardingPreferencesForm profile={profile.data} />
}

export { OnboardingPreferencesForm, OnboardingPreferencesPage }
