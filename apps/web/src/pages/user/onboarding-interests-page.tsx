import { useMemo, useState, type FormEvent } from 'react'
import { CheckCircle2, LoaderCircle, Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import {
  MAX_INTERESTS,
  MAX_LANGUAGES,
  type CatalogLocale,
  type CustomLanguageSelection,
  type CustomPreferenceSelection,
  type LanguageProficiency,
  type ProfileLanguageSelection,
  type ProfilePreferenceSnapshot,
} from '@/features/profile/profile-catalog'
import type { PreferenceTagMessages } from '@/features/profile/preference-tag-input'
import { PreferenceTagInput } from '@/features/profile/preference-tag-input'
import type { OwnProfile } from '@/features/profile/profile'
import type { ProfileFormMode, ReloadOwnProfile } from '@/features/profile/profile-form'
import {
  useInterestCatalog,
  useLanguageCatalog,
} from '@/features/profile/queries/use-profile-catalogs'
import {
  useOwnProfile,
  useProfilePreferences,
  useUpdateProfilePreferences,
} from '@/features/profile/queries/use-own-profile'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'

const PROFICIENCIES: readonly LanguageProficiency[] = [
  'native',
  'fluent',
  'intermediate',
  'beginner',
]

const inputClassName =
  'h-11 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none transition placeholder:text-muted-foreground/70 hover:border-foreground/25 focus-visible:border-vgu-orange focus-visible:ring-2 focus-visible:ring-vgu-orange/25 disabled:cursor-not-allowed disabled:opacity-60'

function selectedValuesMatch(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && left.every((value) => right.includes(value))
}

function customSelectionsMatch(
  left: readonly CustomPreferenceSelection[],
  right: readonly CustomPreferenceSelection[],
): boolean {
  return (
    left.length === right.length && left.every(({ label }, index) => right[index]?.label === label)
  )
}

function languageSelectionsMatch(
  left: readonly ProfileLanguageSelection[],
  right: readonly ProfileLanguageSelection[],
): boolean {
  if (left.length !== right.length) return false
  return left.every(({ language_code, proficiency }) =>
    right.some(
      (selection) =>
        selection.language_code === language_code && selection.proficiency === proficiency,
    ),
  )
}

function customLanguagesMatch(
  left: readonly CustomLanguageSelection[],
  right: readonly CustomLanguageSelection[],
): boolean {
  return (
    left.length === right.length &&
    left.every(
      ({ label, proficiency }, index) =>
        right[index]?.label === label && right[index]?.proficiency === proficiency,
    )
  )
}

function catalogLocale(language: string | undefined): CatalogLocale {
  return language?.split('-')[0] === 'de' ? 'de' : 'en'
}

function CatalogLoading({ label }: { label: string }) {
  return (
    <div
      className="flex min-h-32 items-center justify-center gap-3 text-muted-foreground"
      role="status"
    >
      <LoaderCircle className="size-5 animate-spin motion-reduce:animate-none" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

function CatalogError({
  message,
  retry,
  onRetry,
}: {
  message: string
  retry: string
  onRetry: () => void
}) {
  return (
    <div className="space-y-3 rounded-xl border border-destructive/40 bg-destructive/5 p-4">
      <p className="text-sm text-destructive" role="alert">
        {message}
      </p>
      <Button type="button" variant="outline" size="sm" onClick={onRetry}>
        {retry}
      </Button>
    </div>
  )
}

function OnboardingInterestsEditor({
  preferences,
  mode,
  onReload,
  reloadPreferences,
}: {
  preferences: ProfilePreferenceSnapshot
  mode: ProfileFormMode
  onReload?: ReloadOwnProfile
  reloadPreferences: () => Promise<ProfilePreferenceSnapshot | undefined>
}) {
  const { t, i18n } = useTranslation()
  const locale = catalogLocale(i18n.resolvedLanguage)
  const alternateLocale: CatalogLocale = locale === 'en' ? 'de' : 'en'
  const interests = useInterestCatalog(locale)
  const alternateInterests = useInterestCatalog(alternateLocale)
  const languages = useLanguageCatalog(locale)
  const alternateLanguages = useLanguageCatalog(alternateLocale)
  const savePreferences = useUpdateProfilePreferences()
  const [selectedInterestIds, setSelectedInterestIds] = useState<string[]>(() => [
    ...preferences.interest_ids,
  ])
  const [customInterests, setCustomInterests] = useState<CustomPreferenceSelection[]>(() =>
    preferences.custom_interests.map((selection) => ({ ...selection })),
  )
  const [selectedLanguages, setSelectedLanguages] = useState<ProfileLanguageSelection[]>(() =>
    preferences.languages.map((selection) => ({ ...selection })),
  )
  const [customLanguages, setCustomLanguages] = useState<CustomLanguageSelection[]>(() =>
    preferences.custom_languages.map((selection) => ({ ...selection })),
  )
  const [newLanguageProficiency, setNewLanguageProficiency] =
    useState<LanguageProficiency>('beginner')
  const [search, setSearch] = useState('')
  const [saved, setSaved] = useState(false)
  const [reloading, setReloading] = useState(false)

  const normalizedSearch = search.trim().normalize('NFKC').toLocaleLowerCase(locale)
  const filteredInterests = useMemo(
    () =>
      interests.data?.items.filter(({ label, code }) => {
        if (!normalizedSearch) return true
        return `${label} ${code}`
          .normalize('NFKC')
          .toLocaleLowerCase(locale)
          .includes(normalizedSearch)
      }) ?? [],
    [interests.data?.items, locale, normalizedSearch],
  )
  const interestCollisionLabels = [
    ...(interests.data?.items.map(({ label }) => label) ?? []),
    ...(alternateInterests.data?.items.map(({ label }) => label) ?? []),
  ]
  const languageCollisionLabels = [
    ...(languages.data?.items.map(({ label }) => label) ?? []),
    ...(alternateLanguages.data?.items.map(({ label }) => label) ?? []),
  ]
  const interestCount = selectedInterestIds.length + customInterests.length
  const languageCount = selectedLanguages.length + customLanguages.length

  const tagMessages = (kind: 'interest' | 'language'): PreferenceTagMessages => ({
    inputLabel: t(`preferenceTags.${kind}.inputLabel`),
    placeholder: t(`preferenceTags.${kind}.placeholder`),
    add: t(`preferenceTags.${kind}.add`),
    customBadge: t('preferenceTags.customBadge'),
    remove: (label) => t('preferenceTags.remove', { label }),
    invalid: t('preferenceTags.invalid'),
    duplicate: t('preferenceTags.duplicate'),
    predefinedCollision: t('preferenceTags.predefinedCollision'),
    limitReached: t('preferenceTags.limitReached'),
    characterCount: (count, maximum) => t('preferenceTags.characterCount', { count, maximum }),
  })

  const clearFeedback = () => {
    setSaved(false)
    savePreferences.reset()
  }

  const toggleInterest = (interestId: string) => {
    clearFeedback()
    setSelectedInterestIds((current) => {
      if (current.includes(interestId)) return current.filter((id) => id !== interestId)
      if (current.length + customInterests.length >= MAX_INTERESTS) return current
      return [...current, interestId]
    })
  }

  const toggleLanguage = (languageCode: string) => {
    clearFeedback()
    setSelectedLanguages((current) => {
      if (current.some(({ language_code }) => language_code === languageCode)) {
        return current.filter(({ language_code }) => language_code !== languageCode)
      }
      if (current.length + customLanguages.length >= MAX_LANGUAGES) return current
      return [...current, { language_code: languageCode, proficiency: 'beginner' }]
    })
  }

  const setProficiency = (languageCode: string, proficiency: LanguageProficiency) => {
    clearFeedback()
    setSelectedLanguages((current) =>
      current.map((selection) =>
        selection.language_code === languageCode ? { ...selection, proficiency } : selection,
      ),
    )
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (savePreferences.isPending || (!interests.data && !languages.data)) return

    const unchanged =
      selectedValuesMatch(selectedInterestIds, preferences.interest_ids) &&
      customSelectionsMatch(customInterests, preferences.custom_interests) &&
      languageSelectionsMatch(selectedLanguages, preferences.languages) &&
      customLanguagesMatch(customLanguages, preferences.custom_languages)
    if (unchanged) {
      savePreferences.reset()
      setSaved(true)
      return
    }

    savePreferences.mutate(
      {
        version: preferences.version,
        interest_ids: selectedInterestIds,
        custom_interests: customInterests,
        languages: selectedLanguages,
        custom_languages: customLanguages,
        activity_ids: [...preferences.activity_ids],
        custom_activities: preferences.custom_activities.map((selection) => ({ ...selection })),
      },
      {
        onSuccess: (result) => {
          setSelectedInterestIds([...result.interest_ids])
          setCustomInterests(result.custom_interests.map((selection) => ({ ...selection })))
          setSelectedLanguages(result.languages.map((selection) => ({ ...selection })))
          setCustomLanguages(result.custom_languages.map((selection) => ({ ...selection })))
          setSaved(true)
        },
      },
    )
  }

  const saveError =
    savePreferences.error instanceof ApiError && savePreferences.error.code === 'validation'
      ? t('onboarding.compatibility.serverValidation')
      : savePreferences.error instanceof ApiError && savePreferences.error.code === 'conflict'
        ? t(mode === 'edit' ? 'profileEdit.conflict' : 'onboarding.compatibility.conflict')
        : t('onboarding.compatibility.saveError')
  const hasConflict =
    savePreferences.error instanceof ApiError && savePreferences.error.code === 'conflict'
  const hasEditableCatalog = Boolean(interests.data || languages.data)

  const reloadSavedProfile = async () => {
    if (!onReload || reloading) return
    setReloading(true)
    const [, refreshedPreferences] = await Promise.all([onReload(), reloadPreferences()])
    setReloading(false)
    if (!refreshedPreferences) return
    setSelectedInterestIds([...refreshedPreferences.interest_ids])
    setCustomInterests(refreshedPreferences.custom_interests.map((selection) => ({ ...selection })))
    setSelectedLanguages(refreshedPreferences.languages.map((selection) => ({ ...selection })))
    setCustomLanguages(refreshedPreferences.custom_languages.map((selection) => ({ ...selection })))
    setSearch('')
    setSaved(false)
    savePreferences.reset()
  }

  const titleId =
    mode === 'edit' ? 'profile-edit-compatibility-title' : 'onboarding-compatibility-title'

  return (
    <section className="min-w-0 space-y-6 py-6" aria-labelledby={titleId}>
      <header className="space-y-2">
        <Typography
          variant="small"
          className="font-semibold uppercase tracking-[0.18em] text-vgu-orange"
        >
          {t(
            mode === 'edit' ? 'profileEdit.compatibilityEyebrow' : 'onboarding.compatibility.step',
          )}
        </Typography>
        <Typography as={mode === 'edit' ? 'h2' : 'h1'} variant="h2" id={titleId}>
          {t(mode === 'edit' ? 'profileEdit.compatibilityTitle' : 'onboarding.compatibility.title')}
        </Typography>
        <Typography variant="muted" className="max-w-3xl text-base leading-7">
          {t(
            mode === 'edit'
              ? 'profileEdit.compatibilitySubtitle'
              : 'onboarding.compatibility.subtitle',
          )}
        </Typography>
      </header>

      <form className="space-y-6" aria-busy={savePreferences.isPending} onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>{t('onboarding.compatibility.interestsTitle')}</CardTitle>
            <CardDescription>
              {t('onboarding.compatibility.interestsDescription', { maximum: MAX_INTERESTS })}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {interests.isPending ? (
              <CatalogLoading label={t('onboarding.compatibility.loadingInterests')} />
            ) : interests.isError ? (
              <CatalogError
                message={t('onboarding.compatibility.interestsError')}
                retry={t('onboarding.compatibility.retry')}
                onRetry={() => void interests.refetch()}
              />
            ) : (
              <>
                <div className="space-y-2">
                  <label htmlFor="interest-search" className="text-sm font-medium">
                    {t('onboarding.compatibility.searchInterests')}
                  </label>
                  <div className="relative">
                    <Search
                      className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <input
                      id="interest-search"
                      type="search"
                      value={search}
                      className={cn(inputClassName, 'pl-10')}
                      placeholder={t('onboarding.compatibility.searchPlaceholder')}
                      onChange={(event) => setSearch(event.target.value)}
                    />
                  </div>
                </div>

                <p id="interest-limit" className="text-sm text-muted-foreground" aria-live="polite">
                  {t('onboarding.compatibility.interestCount', {
                    count: interestCount,
                    maximum: MAX_INTERESTS,
                  })}
                </p>

                {filteredInterests.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-border p-5 text-sm text-muted-foreground">
                    {t(
                      search
                        ? 'onboarding.compatibility.noInterestResults'
                        : 'onboarding.compatibility.noInterests',
                    )}
                  </p>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {filteredInterests.map((interest) => {
                      const checked = selectedInterestIds.includes(interest.id)
                      const disabled =
                        savePreferences.isPending || (!checked && interestCount >= MAX_INTERESTS)
                      return (
                        <label
                          key={interest.id}
                          className={cn(
                            'flex min-w-0 cursor-pointer items-center gap-3 rounded-xl border border-border p-3 transition hover:border-vgu-orange/70',
                            checked && 'border-vgu-orange bg-vgu-orange/5',
                            disabled && 'cursor-not-allowed opacity-60',
                          )}
                        >
                          <input
                            type="checkbox"
                            name="interest"
                            value={interest.id}
                            checked={checked}
                            disabled={disabled}
                            aria-describedby="interest-limit"
                            className="size-4 shrink-0 accent-vgu-orange focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange"
                            onChange={() => toggleInterest(interest.id)}
                          />
                          <span className="min-w-0 break-words text-sm font-medium">
                            {interest.label}
                          </span>
                        </label>
                      )
                    })}
                  </div>
                )}

                <PreferenceTagInput
                  values={customInterests}
                  collisionLabels={interestCollisionLabels}
                  selectedCount={interestCount}
                  maximum={MAX_INTERESTS}
                  disabled={savePreferences.isPending}
                  messages={tagMessages('interest')}
                  onAdd={(label) => {
                    clearFeedback()
                    setCustomInterests((current) => [...current, { label }])
                  }}
                  onRemove={(index) => {
                    clearFeedback()
                    setCustomInterests((current) =>
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
            <CardTitle>{t('onboarding.compatibility.languagesTitle')}</CardTitle>
            <CardDescription>
              {t('onboarding.compatibility.languagesDescription', { maximum: MAX_LANGUAGES })}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {languages.isPending ? (
              <CatalogLoading label={t('onboarding.compatibility.loadingLanguages')} />
            ) : languages.isError ? (
              <CatalogError
                message={t('onboarding.compatibility.languagesError')}
                retry={t('onboarding.compatibility.retry')}
                onRetry={() => void languages.refetch()}
              />
            ) : (
              <>
                <p id="language-limit" className="text-sm text-muted-foreground" aria-live="polite">
                  {t('onboarding.compatibility.languageCount', {
                    count: languageCount,
                    maximum: MAX_LANGUAGES,
                  })}
                </p>
                {languages.data.items.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-border p-5 text-sm text-muted-foreground">
                    {t('onboarding.compatibility.noLanguages')}
                  </p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {languages.data.items.map((language) => {
                      const selection = selectedLanguages.find(
                        ({ language_code }) => language_code === language.code,
                      )
                      const disabled =
                        savePreferences.isPending || (!selection && languageCount >= MAX_LANGUAGES)
                      return (
                        <div
                          key={language.code}
                          className={cn(
                            'space-y-3 rounded-xl border border-border p-4 transition',
                            selection && 'border-vgu-orange bg-vgu-orange/5',
                          )}
                        >
                          <label
                            className={cn(
                              'flex cursor-pointer items-center gap-3',
                              disabled && 'cursor-not-allowed opacity-60',
                            )}
                          >
                            <input
                              type="checkbox"
                              name="language"
                              value={language.code}
                              checked={Boolean(selection)}
                              disabled={disabled}
                              aria-describedby="language-limit"
                              className="size-4 shrink-0 accent-vgu-orange focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange"
                              onChange={() => toggleLanguage(language.code)}
                            />
                            <span className="text-sm font-semibold">{language.label}</span>
                          </label>
                          {selection ? (
                            <div className="space-y-2">
                              <label
                                htmlFor={`proficiency-${language.code}`}
                                className="text-sm text-muted-foreground"
                              >
                                {t('onboarding.compatibility.proficiencyFor', {
                                  language: language.label,
                                })}
                              </label>
                              <select
                                id={`proficiency-${language.code}`}
                                value={selection.proficiency}
                                disabled={savePreferences.isPending}
                                className={inputClassName}
                                onChange={(event) =>
                                  setProficiency(
                                    language.code,
                                    event.target.value as LanguageProficiency,
                                  )
                                }
                              >
                                {PROFICIENCIES.map((proficiency) => (
                                  <option key={proficiency} value={proficiency}>
                                    {t(`onboarding.compatibility.proficiencies.${proficiency}`)}
                                  </option>
                                ))}
                              </select>
                            </div>
                          ) : null}
                        </div>
                      )
                    })}
                  </div>
                )}

                <PreferenceTagInput
                  values={customLanguages}
                  collisionLabels={languageCollisionLabels}
                  selectedCount={languageCount}
                  maximum={MAX_LANGUAGES}
                  disabled={savePreferences.isPending}
                  messages={tagMessages('language')}
                  inputAccessory={
                    <label className="space-y-2 text-sm font-medium">
                      <span>{t('preferenceTags.language.proficiency')}</span>
                      <select
                        value={newLanguageProficiency}
                        disabled={savePreferences.isPending || languageCount >= MAX_LANGUAGES}
                        className={cn(inputClassName, 'sm:w-44')}
                        onChange={(event) =>
                          setNewLanguageProficiency(event.target.value as LanguageProficiency)
                        }
                      >
                        {PROFICIENCIES.map((proficiency) => (
                          <option key={proficiency} value={proficiency}>
                            {t(`onboarding.compatibility.proficiencies.${proficiency}`)}
                          </option>
                        ))}
                      </select>
                    </label>
                  }
                  renderValueControl={(value, index) => (
                    <label className="ml-auto">
                      <span className="sr-only">
                        {t('onboarding.compatibility.proficiencyFor', {
                          language: value.label,
                        })}
                      </span>
                      <select
                        value={value.proficiency}
                        disabled={savePreferences.isPending}
                        className="h-9 rounded-md border border-input bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange"
                        onChange={(event) => {
                          clearFeedback()
                          setCustomLanguages((current) =>
                            current.map((selection, itemIndex) =>
                              itemIndex === index
                                ? {
                                    ...selection,
                                    proficiency: event.target.value as LanguageProficiency,
                                  }
                                : selection,
                            ),
                          )
                        }}
                      >
                        {PROFICIENCIES.map((proficiency) => (
                          <option key={proficiency} value={proficiency}>
                            {t(`onboarding.compatibility.proficiencies.${proficiency}`)}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  onAdd={(label) => {
                    clearFeedback()
                    setCustomLanguages((current) => [
                      ...current,
                      { label, proficiency: newLanguageProficiency },
                    ])
                  }}
                  onRemove={(index) => {
                    clearFeedback()
                    setCustomLanguages((current) =>
                      current.filter((_, itemIndex) => itemIndex !== index),
                    )
                  }}
                />
              </>
            )}
          </CardContent>
        </Card>

        <div className="flex flex-col-reverse gap-3 rounded-2xl border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-h-6" aria-live="polite">
            {saved ? (
              <p
                className="flex items-center gap-2 text-sm font-medium text-emerald-600"
                role="status"
              >
                <CheckCircle2 className="size-4" aria-hidden="true" />
                {t(
                  mode === 'edit'
                    ? 'profileEdit.compatibilitySaved'
                    : 'onboarding.compatibility.saved',
                )}
              </p>
            ) : savePreferences.isError ? (
              <div className="space-y-2">
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
          </div>
          <Button
            type="submit"
            disabled={savePreferences.isPending || !hasEditableCatalog}
            className="sm:min-w-40"
          >
            {savePreferences.isPending
              ? t('onboarding.compatibility.saving')
              : t(
                  mode === 'edit'
                    ? 'profileEdit.saveCompatibility'
                    : 'onboarding.compatibility.save',
                )}
          </Button>
        </div>
      </form>
    </section>
  )
}

function OnboardingInterestsForm({
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
      <section className="py-6" aria-busy="true">
        <CatalogLoading label={t('onboarding.compatibility.loadingPreferences')} />
      </section>
    )
  }
  if (preferences.isError) {
    return (
      <section className="py-6">
        <CatalogError
          message={t('onboarding.compatibility.preferencesError')}
          retry={t('onboarding.compatibility.retry')}
          onRetry={() => void preferences.refetch()}
        />
      </section>
    )
  }

  const reloadPreferences = async () => {
    const result = await preferences.refetch()
    return result.isError ? undefined : result.data
  }

  return (
    <OnboardingInterestsEditor
      key={profile.id}
      preferences={preferences.data}
      mode={mode}
      onReload={onReload}
      reloadPreferences={reloadPreferences}
    />
  )
}

function OnboardingInterestsPage() {
  const { t } = useTranslation()
  const profile = useOwnProfile()

  if (profile.isPending) {
    return (
      <section className="flex min-h-72 items-center justify-center py-6" aria-busy="true">
        <CatalogLoading label={t('onboarding.compatibility.loadingProfile')} />
      </section>
    )
  }

  if (profile.isError) {
    return (
      <section className="py-6" aria-labelledby="onboarding-compatibility-load-title">
        <Card className="mx-auto max-w-2xl">
          <CardHeader>
            <CardTitle id="onboarding-compatibility-load-title">
              {t('onboarding.compatibility.profileErrorTitle')}
            </CardTitle>
            <CardDescription role="alert">
              {t('onboarding.compatibility.profileError')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" onClick={() => void profile.refetch()}>
              {t('onboarding.compatibility.retry')}
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }

  return <OnboardingInterestsForm profile={profile.data} />
}

export { OnboardingInterestsForm, OnboardingInterestsPage }
