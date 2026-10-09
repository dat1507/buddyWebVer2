import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'
import type { AdminEvent } from '@/features/admin-events/admin-events'
import { EventEditorForm } from '@/features/admin-events/event-editor-form'
import { emptyEventFormValues, eventFormPayload } from '@/features/admin-events/event-form'
import {
  useCreateAdminEvent,
  useUpdateAdminEvent,
  useUploadAdminEventCover,
} from '@/features/admin-events/queries/use-admin-events'
import { ApiError } from '@/lib/api'

function AdminEventCreatePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const create = useCreateAdminEvent()
  const update = useUpdateAdminEvent()
  const upload = useUploadAdminEventCover()
  const [draft, setDraft] = useState<AdminEvent | null>(null)
  const [serverError, setServerError] = useState<string | null>(null)
  const [recoveryMessage, setRecoveryMessage] = useState<string | null>(null)
  const isPending = create.isPending || update.isPending || upload.isPending

  const failureMessage = (error: unknown) => {
    if (error instanceof ApiError && error.code === 'validation') {
      return t('adminEventForm.errors.validation')
    }
    if (error instanceof ApiError && error.code === 'conflict') {
      return t('adminEventForm.errors.conflict')
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
          {t('adminEventForm.createTitle')}
        </Typography>
        <Typography variant="lead" className="max-w-3xl">
          {t('adminEventForm.createDescription')}
        </Typography>
      </header>

      <EventEditorForm
        initialValues={emptyEventFormValues}
        submitLabel={draft ? t('adminEventForm.retryDraft') : t('adminEventForm.createDraft')}
        pendingLabel={t('adminEventForm.saving')}
        isPending={isPending}
        serverError={serverError}
        recoveryMessage={recoveryMessage}
        onSubmit={async (values, cover) => {
          setServerError(null)
          setRecoveryMessage(null)
          let current = draft
          try {
            current = current
              ? await update.mutateAsync({
                  eventId: current.id,
                  payload: { ...eventFormPayload(values), version: current.version },
                })
              : await create.mutateAsync(eventFormPayload(values))
            setDraft(current)
          } catch (error) {
            setServerError(failureMessage(error))
            return
          }

          if (cover) {
            try {
              const result = await upload.mutateAsync({
                eventId: current.id,
                version: current.version,
                altEn: values.altEn,
                altDe: values.altDe,
                file: cover,
              })
              current = result.event
              setDraft(current)
            } catch {
              setRecoveryMessage(t('adminEventForm.errors.draftSavedCoverFailed'))
              return
            }
          }
          navigate(`/admin/events/${current.id}/edit`, { replace: true })
        }}
      />
    </section>
  )
}

export { AdminEventCreatePage }
