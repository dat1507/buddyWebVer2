import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { ImagePlus, LoaderCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  validateEventForm,
  type EventFormErrors,
  type EventFormValues,
} from '@/features/admin-events/event-form'

interface EventEditorFormProps {
  initialValues: EventFormValues
  submitLabel: string
  pendingLabel: string
  isPending: boolean
  existingCoverUrl?: string | null
  serverError?: string | null
  successMessage?: string | null
  recoveryMessage?: string | null
  resetFileToken?: number
  onSubmit: (values: EventFormValues, cover: File | null) => Promise<void>
}

const inputClassName =
  'h-10 w-full min-w-0 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60'
const textareaClassName = `${inputClassName} min-h-28 py-2`

function EventEditorForm({
  initialValues,
  submitLabel,
  pendingLabel,
  isPending,
  existingCoverUrl = null,
  serverError = null,
  successMessage = null,
  recoveryMessage = null,
  resetFileToken = 0,
  onSubmit,
}: EventEditorFormProps) {
  const { t } = useTranslation()
  const formId = useId()
  const [values, setValues] = useState(initialValues)
  const [coverSelection, setCoverSelection] = useState<{
    token: number
    file: File | null
  }>({ token: resetFileToken, file: null })
  const [errors, setErrors] = useState<EventFormErrors>({})
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const previewUrlRef = useRef<string | null>(null)
  const submitLockedRef = useRef(false)
  const initialSnapshot = useMemo(() => JSON.stringify(initialValues), [initialValues])
  const cover = coverSelection.token === resetFileToken ? coverSelection.file : null
  const isDirty = JSON.stringify(values) !== initialSnapshot || cover !== null

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    }
  }, [])

  useEffect(() => {
    if (coverSelection.token === resetFileToken || !previewUrlRef.current) return
    URL.revokeObjectURL(previewUrlRef.current)
    previewUrlRef.current = null
  }, [coverSelection.token, resetFileToken])

  useEffect(() => {
    if (!isDirty || isPending) return
    const warn = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [isDirty, isPending])

  const set = <Key extends keyof EventFormValues>(key: Key, value: EventFormValues[Key]) => {
    setValues((current) => ({ ...current, [key]: value }))
    setErrors((current) => ({ ...current, [key]: undefined }))
  }
  const error = (field: keyof EventFormErrors) =>
    errors[field] ? (
      <p id={`${formId}-${field}-error`} className="text-sm text-destructive" role="alert">
        {errors[field]}
      </p>
    ) : null
  const describedBy = (field: keyof EventFormErrors) =>
    errors[field] ? `${formId}-${field}-error` : undefined
  const validateMessage = (key: string) => t(`adminEventForm.validation.${key}`)

  return (
    <form
      className="space-y-6"
      noValidate
      onSubmit={async (event) => {
        event.preventDefault()
        if (isPending || submitLockedRef.current) return
        const nextErrors = validateEventForm(values, cover, validateMessage)
        setErrors(nextErrors)
        if (Object.keys(nextErrors).length) return
        submitLockedRef.current = true
        try {
          await onSubmit(values, cover)
        } finally {
          submitLockedRef.current = false
        }
      }}
    >
      {serverError ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {serverError}
        </p>
      ) : null}
      {recoveryMessage ? (
        <p
          role="status"
          className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-800 dark:text-amber-200"
        >
          {recoveryMessage}
        </p>
      ) : null}
      {successMessage ? (
        <p
          role="status"
          className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-800 dark:text-emerald-200"
        >
          {successMessage}
        </p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t('adminEventForm.content.title')}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          {(['En', 'De'] as const).map((locale) => {
            const title = `title${locale}` as const
            const description = `description${locale}` as const
            const location = `location${locale}` as const
            return (
              <fieldset key={locale} className="space-y-4 rounded-lg border p-4">
                <legend className="px-2 font-semibold">
                  {t(`adminEventForm.locale.${locale.toLowerCase()}`)}
                </legend>
                <label className="block space-y-1 text-sm font-medium">
                  {t('adminEventForm.content.eventTitle')}
                  <input
                    value={values[title]}
                    maxLength={120}
                    disabled={isPending}
                    className={inputClassName}
                    aria-describedby={describedBy(title)}
                    onChange={(event) => set(title, event.target.value)}
                  />
                  {error(title)}
                </label>
                <label className="block space-y-1 text-sm font-medium">
                  {t('adminEventForm.content.description')}
                  <textarea
                    value={values[description]}
                    maxLength={10_000}
                    disabled={isPending}
                    className={textareaClassName}
                    aria-describedby={describedBy(description)}
                    onChange={(event) => set(description, event.target.value)}
                  />
                  {error(description)}
                </label>
                <label className="block space-y-1 text-sm font-medium">
                  {t('adminEventForm.content.location')}
                  <input
                    value={values[location]}
                    maxLength={200}
                    disabled={isPending}
                    className={inputClassName}
                    aria-describedby={describedBy(location)}
                    onChange={(event) => set(location, event.target.value)}
                  />
                  {error(location)}
                </label>
              </fieldset>
            )
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('adminEventForm.schedule.title')}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1 text-sm font-medium">
            {t('adminEventForm.schedule.start')}
            <input
              type="datetime-local"
              value={values.startDate}
              disabled={isPending}
              className={inputClassName}
              aria-describedby={describedBy('startDate')}
              onChange={(event) => set('startDate', event.target.value)}
            />
            {error('startDate')}
          </label>
          <label className="space-y-1 text-sm font-medium">
            {t('adminEventForm.schedule.end')}
            <input
              type="datetime-local"
              value={values.endDate}
              disabled={isPending}
              className={inputClassName}
              aria-describedby={describedBy('endDate')}
              onChange={(event) => set('endDate', event.target.value)}
            />
            {error('endDate')}
          </label>
          <label className="space-y-1 text-sm font-medium">
            {t('adminEventForm.schedule.timezone')}
            <input
              value={values.timezone}
              maxLength={255}
              disabled={isPending}
              className={inputClassName}
              aria-describedby={describedBy('timezone')}
              onChange={(event) => set('timezone', event.target.value)}
            />
            {error('timezone')}
          </label>
          <label className="space-y-1 text-sm font-medium">
            {t('adminEventForm.schedule.deadline')}
            <input
              type="datetime-local"
              value={values.registrationDeadline}
              disabled={isPending}
              className={inputClassName}
              aria-describedby={describedBy('registrationDeadline')}
              onChange={(event) => set('registrationDeadline', event.target.value)}
            />
            {error('registrationDeadline')}
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('adminEventForm.details.title')}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1 text-sm font-medium">
            {t('adminEventForm.details.category')}
            <input
              value={values.category}
              maxLength={80}
              disabled={isPending}
              className={inputClassName}
              aria-describedby={describedBy('category')}
              onChange={(event) => set('category', event.target.value)}
            />
            {error('category')}
          </label>
          <label className="space-y-1 text-sm font-medium">
            {t('adminEventForm.details.organizer')}
            <input
              value={values.organizer}
              maxLength={200}
              disabled={isPending}
              className={inputClassName}
              aria-describedby={describedBy('organizer')}
              onChange={(event) => set('organizer', event.target.value)}
            />
            {error('organizer')}
          </label>
          <label className="space-y-1 text-sm font-medium">
            {t('adminEventForm.details.visibility')}
            <select
              value={values.visibility}
              disabled={isPending}
              className={inputClassName}
              onChange={(event) =>
                set('visibility', event.target.value as EventFormValues['visibility'])
              }
            >
              <option value="MEMBERS">{t('adminEvents.visibility.MEMBERS')}</option>
              <option value="PUBLIC">{t('adminEvents.visibility.PUBLIC')}</option>
            </select>
          </label>
          <label className="space-y-1 text-sm font-medium">
            {t('adminEventForm.details.capacity')}
            <input
              type="number"
              min="1"
              step="1"
              value={values.maxParticipants}
              disabled={isPending}
              className={inputClassName}
              aria-describedby={describedBy('maxParticipants')}
              onChange={(event) => set('maxParticipants', event.target.value)}
            />
            {error('maxParticipants')}
          </label>
          <label className="space-y-1 text-sm font-medium sm:col-span-2">
            {t('adminEventForm.details.registrationUrl')}
            <input
              type="url"
              value={values.registrationUrl}
              maxLength={2048}
              disabled={isPending}
              className={inputClassName}
              placeholder="https://"
              aria-describedby={describedBy('registrationUrl')}
              onChange={(event) => set('registrationUrl', event.target.value)}
            />
            {error('registrationUrl')}
          </label>
          <label className="flex items-center gap-3 text-sm font-medium sm:col-span-2">
            <input
              type="checkbox"
              checked={values.registrationEnabled}
              disabled={isPending}
              onChange={(event) => set('registrationEnabled', event.target.checked)}
            />
            {t('adminEventForm.details.registrationEnabled')}
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('adminEventForm.cover.title')}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(14rem,0.6fr)]">
          <div className="space-y-4">
            <label className="block space-y-1 text-sm font-medium">
              {t(existingCoverUrl ? 'adminEventForm.cover.replace' : 'adminEventForm.cover.choose')}
              <input
                key={resetFileToken}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                disabled={isPending}
                className={inputClassName}
                aria-describedby={describedBy('cover')}
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null
                  if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
                  const nextPreview =
                    file && typeof URL.createObjectURL === 'function'
                      ? URL.createObjectURL(file)
                      : null
                  previewUrlRef.current = nextPreview
                  setPreviewUrl(nextPreview)
                  setCoverSelection({ token: resetFileToken, file })
                  setErrors((current) => ({ ...current, cover: undefined }))
                }}
              />
              {error('cover')}
            </label>
            <p className="text-sm text-muted-foreground">{t('adminEventForm.cover.help')}</p>
            <label className="block space-y-1 text-sm font-medium">
              {t('adminEventForm.cover.altEn')}
              <input
                value={values.altEn}
                maxLength={200}
                disabled={isPending}
                className={inputClassName}
                aria-describedby={describedBy('altEn')}
                onChange={(event) => set('altEn', event.target.value)}
              />
              {error('altEn')}
            </label>
            <label className="block space-y-1 text-sm font-medium">
              {t('adminEventForm.cover.altDe')}
              <input
                value={values.altDe}
                maxLength={200}
                disabled={isPending}
                className={inputClassName}
                aria-describedby={describedBy('altDe')}
                onChange={(event) => set('altDe', event.target.value)}
              />
              {error('altDe')}
            </label>
          </div>
          <div className="flex min-h-48 items-center justify-center overflow-hidden rounded-lg border bg-muted/40">
            {(cover ? previewUrl : null) || existingCoverUrl ? (
              <img
                src={(cover ? previewUrl : null) ?? existingCoverUrl ?? ''}
                alt={values.altEn || t('adminEventForm.cover.preview')}
                className="max-h-80 w-full object-contain"
              />
            ) : (
              <div className="space-y-2 text-center text-muted-foreground">
                <ImagePlus aria-hidden="true" className="mx-auto size-8" />
                <p>{t('adminEventForm.cover.empty')}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={isPending} aria-busy={isPending}>
          {isPending ? (
            <LoaderCircle aria-hidden="true" className="animate-spin motion-reduce:animate-none" />
          ) : null}
          {isPending ? pendingLabel : submitLabel}
        </Button>
        {isDirty ? (
          <p className="text-sm text-muted-foreground">{t('adminEventForm.unsaved')}</p>
        ) : null}
      </div>
    </form>
  )
}

export { EventEditorForm }
