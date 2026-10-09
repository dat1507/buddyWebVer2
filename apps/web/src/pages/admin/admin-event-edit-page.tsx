import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'
import { EventEditorForm } from '@/features/admin-events/event-editor-form'
import { eventFormPayload, eventToFormValues } from '@/features/admin-events/event-form'
import { EventStatusControls } from '@/features/admin-events/event-status-controls'
import {
  useAdminEventCover,
  useAdminEventDetail,
  useUpdateAdminEvent,
  useUploadAdminEventCover,
} from '@/features/admin-events/queries/use-admin-events'
import { ApiError } from '@/lib/api'

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function AdminEventEditPage() {
  const { t } = useTranslation()
  const { eventId: routeEventId } = useParams()
  const eventId = routeEventId && uuidPattern.test(routeEventId) ? routeEventId : null
  const detail = useAdminEventDetail(eventId)
  const cover = useAdminEventCover(eventId, detail.data?.cover_media_id ?? null)
  const update = useUpdateAdminEvent()
  const upload = useUploadAdminEventCover()
  const [serverError, setServerError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [recoveryMessage, setRecoveryMessage] = useState<string | null>(null)
  const [resetFileToken, setResetFileToken] = useState(0)
  const initialValues = useMemo(
    () => (detail.data ? eventToFormValues(detail.data) : null),
    [detail.data],
  )

  if (
    !eventId ||
    (detail.isError && detail.error instanceof ApiError && detail.error.code === 'notFound')
  ) {
    return (
      <section className="space-y-4 py-6">
        <Typography as="h1" variant="h2">
          {t('adminEventForm.notFound.title')}
        </Typography>
        <Typography variant="lead">{t('adminEventForm.notFound.description')}</Typography>
        <Button asChild variant="outline">
          <Link to="/admin/events">{t('adminEventForm.back')}</Link>
        </Button>
      </section>
    )
  }
  if (detail.isError) {
    return (
      <section className="space-y-4 py-6">
        <p role="alert">{t('adminEventForm.errors.load')}</p>
        <Button type="button" variant="outline" onClick={() => void detail.refetch()}>
          {t('dataTable.retry')}
        </Button>
      </section>
    )
  }
  if (detail.isPending || !initialValues) {
    return (
      <p role="status" className="py-8">
        {t('adminEventForm.loading')}
      </p>
    )
  }

  const current = detail.data
  const isPending = update.isPending || upload.isPending
  const saveError = (error: unknown) => {
    if (error instanceof ApiError && error.code === 'conflict') {
      return t('adminEventForm.errors.conflictReload')
    }
    if (error instanceof ApiError && error.code === 'validation') {
      return t('adminEventForm.errors.validation')
    }
    return t('adminEventForm.errors.save')
  }

  return (
    <section className="min-w-0 space-y-6 py-6">
      <header className="space-y-3">
        <Button asChild variant="link" className="px-0">
          <Link to="/admin/events">{t('adminEventForm.back')}</Link>
        </Button>
        <Typography as="h1" variant="h2" className="break-words text-3xl sm:text-4xl">
          {t('adminEventForm.editTitle')}
        </Typography>
        <Typography variant="lead" className="max-w-3xl">
          {t('adminEventForm.editDescription')}
        </Typography>
      </header>

      <EventStatusControls event={current} disabled={isPending} />

      <EventEditorForm
        initialValues={initialValues}
        existingCoverUrl={cover.data?.url ?? null}
        submitLabel={t('adminEventForm.save')}
        pendingLabel={t('adminEventForm.saving')}
        isPending={isPending}
        serverError={serverError}
        successMessage={successMessage}
        recoveryMessage={recoveryMessage}
        resetFileToken={resetFileToken}
        onSubmit={async (values, replacement) => {
          setServerError(null)
          setSuccessMessage(null)
          setRecoveryMessage(null)
          let updated
          try {
            updated = await update.mutateAsync({
              eventId: current.id,
              payload: { ...eventFormPayload(values), version: current.version },
            })
          } catch (error) {
            setServerError(saveError(error))
            return
          }
          if (replacement) {
            try {
              const result = await upload.mutateAsync({
                eventId: updated.id,
                version: updated.version,
                altEn: values.altEn,
                altDe: values.altDe,
                file: replacement,
              })
              setSuccessMessage(
                result.cleanup_pending
                  ? t('adminEventForm.savedCleanupPending')
                  : t('adminEventForm.saved'),
              )
              setResetFileToken((value) => value + 1)
            } catch {
              setRecoveryMessage(t('adminEventForm.errors.contentSavedCoverFailed'))
            }
            return
          }
          setSuccessMessage(t('adminEventForm.saved'))
        }}
      />
    </section>
  )
}

export { AdminEventEditPage }
