import { useRef, useState, type FormEvent } from 'react'
import { CheckCircle2, LoaderCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { ProfileAvatarControl } from '@/features/profile/profile-avatar-control'
import type { ProfileFormMode, ReloadOwnProfile } from '@/features/profile/profile-form'
import type { OwnProfile, OwnProfileUpdate, StudentType } from '@/features/profile/profile'
import { useOwnProfile, useUpdateOwnProfile } from '@/features/profile/queries/use-own-profile'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'

type FormField = 'fullName' | 'displayName' | 'studentType' | 'studyYear' | 'bio'
type FormErrors = Partial<Record<FormField, string>>

interface IdentityFormState {
  fullName: string
  displayName: string
  studentType: StudentType | ''
  major: string
  studyYear: string
  nationality: string
  bio: string
}

const inputClassName =
  'h-11 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none transition placeholder:text-muted-foreground/70 hover:border-foreground/25 focus-visible:border-vgu-orange focus-visible:ring-2 focus-visible:ring-vgu-orange/25 disabled:cursor-not-allowed disabled:opacity-60'

function profileToForm(profile: OwnProfile): IdentityFormState {
  return {
    fullName: profile.full_name ?? '',
    displayName: profile.display_name ?? '',
    studentType: profile.student_type ?? '',
    major: profile.major ?? '',
    studyYear: profile.study_year?.toString() ?? '',
    nationality: profile.nationality ?? '',
    bio: profile.bio ?? '',
  }
}

function optionalText(value: string): string | null {
  const normalized = value.trim()
  return normalized || null
}

function OnboardingIdentityForm({
  initialProfile,
  mode = 'onboarding',
  onReload,
}: {
  initialProfile: OwnProfile
  mode?: ProfileFormMode
  onReload?: ReloadOwnProfile
}) {
  const { t } = useTranslation()
  const updateProfile = useUpdateOwnProfile()
  const [form, setForm] = useState<IdentityFormState>(() => profileToForm(initialProfile))
  const [errors, setErrors] = useState<FormErrors>({})
  const [saved, setSaved] = useState(false)
  const [reloading, setReloading] = useState(false)
  const fullNameRef = useRef<HTMLInputElement>(null)
  const displayNameRef = useRef<HTMLInputElement>(null)
  const vietnameseTypeRef = useRef<HTMLInputElement>(null)
  const studyYearRef = useRef<HTMLInputElement>(null)
  const bioRef = useRef<HTMLTextAreaElement>(null)

  const setField = <Field extends keyof IdentityFormState>(
    field: Field,
    value: IdentityFormState[Field],
  ) => {
    setForm((current) => ({ ...current, [field]: value }))
    setSaved(false)
    updateProfile.reset()
    if (field in errors) {
      setErrors((current) => ({ ...current, [field]: undefined }))
    }
  }

  const validate = (): FormErrors => {
    const next: FormErrors = {}
    const fullNameLength = [...form.fullName.trim()].length
    const displayNameLength = [...form.displayName.trim()].length
    const bioLength = [...form.bio.trim()].length

    if (fullNameLength === 0) next.fullName = t('onboarding.identity.validation.fullNameRequired')
    else if (fullNameLength > 120)
      next.fullName = t('onboarding.identity.validation.fullNameMaximum')
    if (displayNameLength > 80)
      next.displayName = t('onboarding.identity.validation.displayNameMaximum')
    if (!form.studentType)
      next.studentType = t('onboarding.identity.validation.studentTypeRequired')
    if (form.studyYear) {
      const year = Number(form.studyYear)
      if (!Number.isInteger(year) || year < 1 || year > 10)
        next.studyYear = t('onboarding.identity.validation.studyYearRange')
    }
    if (bioLength > 500) next.bio = t('onboarding.identity.validation.bioMaximum')
    return next
  }

  const focusFirstInvalidField = (nextErrors: FormErrors) => {
    const fields = [
      ['fullName', fullNameRef],
      ['displayName', displayNameRef],
      ['studentType', vietnameseTypeRef],
      ['studyYear', studyYearRef],
      ['bio', bioRef],
    ] as const
    fields.find(([field]) => nextErrors[field])?.[1].current?.focus()
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (updateProfile.isPending) return
    const nextErrors = validate()
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      focusFirstInvalidField(nextErrors)
      return
    }

    const update: OwnProfileUpdate = {
      version: initialProfile.version,
      full_name: form.fullName.trim(),
      display_name: optionalText(form.displayName),
      student_type: form.studentType as StudentType,
      major: optionalText(form.major),
      study_year: form.studyYear ? Number(form.studyYear) : null,
      nationality: optionalText(form.nationality),
      bio: optionalText(form.bio),
    }
    updateProfile.mutate(update, {
      onSuccess: (savedProfile) => {
        setForm(profileToForm(savedProfile))
        setSaved(true)
      },
    })
  }

  const saveError =
    updateProfile.error instanceof ApiError && updateProfile.error.code === 'validation'
      ? t('onboarding.identity.serverValidation')
      : updateProfile.error instanceof ApiError && updateProfile.error.code === 'conflict'
        ? t(mode === 'edit' ? 'profileEdit.conflict' : 'onboarding.identity.conflict')
        : t('onboarding.identity.saveError')
  const hasConflict =
    updateProfile.error instanceof ApiError && updateProfile.error.code === 'conflict'

  const reloadSavedProfile = async () => {
    if (!onReload || reloading) return
    setReloading(true)
    const refreshedProfile = await onReload()
    setReloading(false)
    if (!refreshedProfile) return
    setForm(profileToForm(refreshedProfile))
    setErrors({})
    setSaved(false)
    updateProfile.reset()
  }

  const titleId = mode === 'edit' ? 'profile-edit-identity-title' : 'onboarding-identity-title'

  return (
    <section className="min-w-0 space-y-6 py-6" aria-labelledby={titleId}>
      <header className="space-y-2">
        <Typography
          variant="small"
          className="font-semibold uppercase tracking-[0.18em] text-vgu-orange"
        >
          {t(mode === 'edit' ? 'profileEdit.identityEyebrow' : 'onboarding.identity.step')}
        </Typography>
        <Typography as={mode === 'edit' ? 'h2' : 'h1'} variant="h2" id={titleId}>
          {t(mode === 'edit' ? 'profileEdit.identityTitle' : 'onboarding.identity.title')}
        </Typography>
        <Typography variant="muted" className="max-w-3xl text-base leading-7">
          {t(mode === 'edit' ? 'profileEdit.identitySubtitle' : 'onboarding.identity.subtitle')}
        </Typography>
      </header>

      <Card className="max-w-4xl">
        <CardHeader>
          <CardTitle>{t('onboarding.identity.cardTitle')}</CardTitle>
          <CardDescription>{t('onboarding.identity.requiredHint')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-7">
          <ProfileAvatarControl profile={initialProfile} />
          <form
            noValidate
            aria-busy={updateProfile.isPending}
            className="space-y-7 border-t border-border pt-7"
            onSubmit={handleSubmit}
          >
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="profile-full-name" className="text-sm font-medium">
                  {t('onboarding.identity.fullNameLabel')}
                </label>
                <input
                  ref={fullNameRef}
                  id="profile-full-name"
                  name="fullName"
                  autoComplete="name"
                  value={form.fullName}
                  disabled={updateProfile.isPending}
                  aria-invalid={Boolean(errors.fullName)}
                  aria-describedby={errors.fullName ? 'profile-full-name-error' : undefined}
                  className={cn(inputClassName, errors.fullName && 'border-destructive')}
                  onChange={(event) => setField('fullName', event.target.value)}
                />
                {errors.fullName ? (
                  <p id="profile-full-name-error" className="text-sm text-destructive">
                    {errors.fullName}
                  </p>
                ) : null}
              </div>

              <div className="space-y-2">
                <label htmlFor="profile-display-name" className="text-sm font-medium">
                  {t('onboarding.identity.displayNameLabel')}{' '}
                  <span className="font-normal text-muted-foreground">
                    {t('onboarding.identity.optional')}
                  </span>
                </label>
                <input
                  ref={displayNameRef}
                  id="profile-display-name"
                  name="displayName"
                  value={form.displayName}
                  disabled={updateProfile.isPending}
                  aria-invalid={Boolean(errors.displayName)}
                  aria-describedby={errors.displayName ? 'profile-display-name-error' : undefined}
                  className={cn(inputClassName, errors.displayName && 'border-destructive')}
                  onChange={(event) => setField('displayName', event.target.value)}
                />
                {errors.displayName ? (
                  <p id="profile-display-name-error" className="text-sm text-destructive">
                    {errors.displayName}
                  </p>
                ) : null}
              </div>
            </div>

            <fieldset
              className="space-y-3"
              aria-describedby={
                errors.studentType ? 'student-type-help student-type-error' : 'student-type-help'
              }
            >
              <legend className="text-sm font-semibold">
                {t('onboarding.identity.studentTypeLabel')}
              </legend>
              <p id="student-type-help" className="text-sm leading-6 text-muted-foreground">
                {t('onboarding.identity.studentTypeHelp')}
              </p>
              <div className="grid gap-3 md:grid-cols-2">
                {(['VIETNAMESE', 'INTERNATIONAL'] as const).map((studentType) => (
                  <label
                    key={studentType}
                    className={cn(
                      'flex cursor-pointer items-start gap-3 rounded-xl border border-border p-4 transition hover:border-vgu-orange/70',
                      form.studentType === studentType && 'border-vgu-orange bg-vgu-orange/5',
                      errors.studentType && 'border-destructive',
                    )}
                  >
                    <input
                      ref={studentType === 'VIETNAMESE' ? vietnameseTypeRef : undefined}
                      type="radio"
                      name="studentType"
                      value={studentType}
                      aria-labelledby={`student-type-${studentType}-label`}
                      aria-describedby={`student-type-${studentType}-help`}
                      checked={form.studentType === studentType}
                      disabled={updateProfile.isPending}
                      className="mt-1 size-4 shrink-0 accent-vgu-orange focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange"
                      onChange={() => setField('studentType', studentType)}
                    />
                    <span>
                      <span
                        id={`student-type-${studentType}-label`}
                        className="block text-sm font-semibold"
                      >
                        {t(`onboarding.identity.studentTypes.${studentType}.label`)}
                      </span>
                      <span
                        id={`student-type-${studentType}-help`}
                        className="mt-1 block text-sm leading-6 text-muted-foreground"
                      >
                        {t(`onboarding.identity.studentTypes.${studentType}.help`)}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
              {errors.studentType ? (
                <p id="student-type-error" className="text-sm text-destructive">
                  {errors.studentType}
                </p>
              ) : null}
            </fieldset>

            <div className="grid gap-5 sm:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="profile-major" className="text-sm font-medium">
                  {t('onboarding.identity.majorLabel')}{' '}
                  <span className="font-normal text-muted-foreground">
                    {t('onboarding.identity.optional')}
                  </span>
                </label>
                <input
                  id="profile-major"
                  name="major"
                  value={form.major}
                  disabled={updateProfile.isPending}
                  className={inputClassName}
                  onChange={(event) => setField('major', event.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="profile-study-year" className="text-sm font-medium">
                  {t('onboarding.identity.studyYearLabel')}{' '}
                  <span className="font-normal text-muted-foreground">
                    {t('onboarding.identity.optional')}
                  </span>
                </label>
                <input
                  ref={studyYearRef}
                  id="profile-study-year"
                  name="studyYear"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={10}
                  value={form.studyYear}
                  disabled={updateProfile.isPending}
                  aria-invalid={Boolean(errors.studyYear)}
                  aria-describedby={errors.studyYear ? 'profile-study-year-error' : undefined}
                  className={cn(inputClassName, errors.studyYear && 'border-destructive')}
                  onChange={(event) => setField('studyYear', event.target.value)}
                />
                {errors.studyYear ? (
                  <p id="profile-study-year-error" className="text-sm text-destructive">
                    {errors.studyYear}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="profile-nationality" className="text-sm font-medium">
                {t('onboarding.identity.nationalityLabel')}{' '}
                <span className="font-normal text-muted-foreground">
                  {t('onboarding.identity.optional')}
                </span>
              </label>
              <input
                id="profile-nationality"
                name="nationality"
                autoComplete="country-name"
                value={form.nationality}
                disabled={updateProfile.isPending}
                className={inputClassName}
                onChange={(event) => setField('nationality', event.target.value)}
              />
              <p className="text-sm leading-6 text-muted-foreground">
                {t('onboarding.identity.nationalityHelp')}
              </p>
            </div>

            <div className="space-y-2">
              <label htmlFor="profile-bio" className="text-sm font-medium">
                {t('onboarding.identity.bioLabel')}{' '}
                <span className="font-normal text-muted-foreground">
                  {t('onboarding.identity.optional')}
                </span>
              </label>
              <textarea
                ref={bioRef}
                id="profile-bio"
                name="bio"
                rows={5}
                value={form.bio}
                disabled={updateProfile.isPending}
                aria-invalid={Boolean(errors.bio)}
                aria-describedby={errors.bio ? 'profile-bio-error' : 'profile-bio-help'}
                className={cn(
                  inputClassName,
                  'h-auto min-h-32 resize-y py-3',
                  errors.bio && 'border-destructive',
                )}
                onChange={(event) => setField('bio', event.target.value)}
              />
              <div className="flex items-start justify-between gap-4 text-sm text-muted-foreground">
                <span id="profile-bio-help">{t('onboarding.identity.bioHelp')}</span>
                <span aria-hidden="true">{[...form.bio].length}/500</span>
              </div>
              {errors.bio ? (
                <p id="profile-bio-error" className="text-sm text-destructive">
                  {errors.bio}
                </p>
              ) : null}
            </div>

            <div className="flex flex-col-reverse gap-3 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-h-6" aria-live="polite">
                {saved ? (
                  <p
                    className="flex items-center gap-2 text-sm font-medium text-emerald-600"
                    role="status"
                  >
                    <CheckCircle2 className="size-4" aria-hidden="true" />
                    {t(mode === 'edit' ? 'profileEdit.identitySaved' : 'onboarding.identity.saved')}
                  </p>
                ) : updateProfile.isError ? (
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
              <Button type="submit" disabled={updateProfile.isPending} className="sm:min-w-40">
                {updateProfile.isPending
                  ? t('onboarding.identity.saving')
                  : t(mode === 'edit' ? 'profileEdit.saveIdentity' : 'onboarding.identity.save')}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </section>
  )
}

function OnboardingIdentityPage() {
  const { t } = useTranslation()
  const profile = useOwnProfile()

  if (profile.isPending) {
    return (
      <section className="flex min-h-72 items-center justify-center py-6" aria-busy="true">
        <div className="flex items-center gap-3 text-muted-foreground" role="status">
          <LoaderCircle
            className="size-5 animate-spin motion-reduce:animate-none"
            aria-hidden="true"
          />
          <span>{t('onboarding.identity.loading')}</span>
        </div>
      </section>
    )
  }

  if (profile.isError) {
    return (
      <section className="py-6" aria-labelledby="onboarding-load-title">
        <Card className="mx-auto max-w-2xl">
          <CardHeader>
            <CardTitle id="onboarding-load-title">
              {t('onboarding.identity.loadErrorTitle')}
            </CardTitle>
            <CardDescription role="alert">{t('onboarding.identity.loadError')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" onClick={() => void profile.refetch()}>
              {t('onboarding.identity.retry')}
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }

  return <OnboardingIdentityForm initialProfile={profile.data} />
}

export { OnboardingIdentityForm, OnboardingIdentityPage }
