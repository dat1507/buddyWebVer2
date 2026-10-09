import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Button } from '@/components/ui/button'
import type { AdminEvent, EventStatus } from '@/features/admin-events/admin-events'
import { useSetAdminEventStatus } from '@/features/admin-events/queries/use-admin-events'
import { ApiError } from '@/lib/api'

const readinessFields = [
  ['title_en', 'adminEventStatus.readiness.titleEn'],
  ['title_de', 'adminEventStatus.readiness.titleDe'],
  ['description_en', 'adminEventStatus.readiness.descriptionEn'],
  ['description_de', 'adminEventStatus.readiness.descriptionDe'],
  ['location_en', 'adminEventStatus.readiness.locationEn'],
  ['location_de', 'adminEventStatus.readiness.locationDe'],
  ['start_date', 'adminEventStatus.readiness.start'],
  ['end_date', 'adminEventStatus.readiness.end'],
  ['cover_media_id', 'adminEventStatus.readiness.cover'],
] as const satisfies ReadonlyArray<readonly [keyof AdminEvent, string]>

function eventPublicationReadiness(event: AdminEvent): readonly string[] {
  const missing = readinessFields
    .filter(([field]) => {
      const value = event[field]
      return value === null || (typeof value === 'string' && value.trim() === '')
    })
    .map(([, translationKey]) => translationKey)

  if (
    event.start_date &&
    event.end_date &&
    new Date(event.end_date).getTime() <= new Date(event.start_date).getTime()
  ) {
    return [...missing, 'adminEventStatus.readiness.endAfterStart']
  }
  return missing
}

interface EventStatusControlsProps {
  event: AdminEvent
  disabled?: boolean
}

function EventStatusControls({ event, disabled = false }: EventStatusControlsProps) {
  const { t } = useTranslation()
  const setStatus = useSetAdminEventStatus()
  const transitionLock = useRef(false)
  const [confirmation, setConfirmation] = useState<EventStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showReadiness, setShowReadiness] = useState(false)
  const missingFields = eventPublicationReadiness(event)

  const transition = async (status: EventStatus) => {
    if (transitionLock.current || setStatus.isPending || status === event.status) return
    if (status === 'PUBLISHED' && missingFields.length > 0) {
      setSuccess(null)
      setError(null)
      setShowReadiness(true)
      return
    }

    transitionLock.current = true
    setError(null)
    setSuccess(null)
    setShowReadiness(false)
    try {
      const updated = await setStatus.mutateAsync({
        eventId: event.id,
        version: event.version,
        status,
      })
      setConfirmation(null)
      setSuccess(
        t('adminEventStatus.success', { status: t(`adminEvents.status.${updated.status}`) }),
      )
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === 'conflict') {
        setError(t('adminEventStatus.errors.conflict'))
      } else if (caught instanceof ApiError && caught.code === 'validation') {
        setError(t('adminEventStatus.errors.validation'))
      } else {
        setError(t('adminEventStatus.errors.save'))
      }
    } finally {
      transitionLock.current = false
    }
  }

  const requestTransition = (status: EventStatus) => {
    if (status === 'PUBLISHED') {
      void transition(status)
      return
    }
    setError(null)
    setSuccess(null)
    setConfirmation(status)
  }

  const isDisabled = disabled || setStatus.isPending

  return (
    <section
      aria-labelledby="event-status-heading"
      className="space-y-4 rounded-2xl border border-border bg-card p-5 shadow-sm"
    >
      <div className="space-y-1">
        <h2 id="event-status-heading" className="text-xl font-semibold">
          {t('adminEventStatus.title')}
        </h2>
        <p className="text-sm text-muted-foreground">
          {t('adminEventStatus.current', { status: t(`adminEvents.status.${event.status}`) })}
          {event.phase
            ? ` · ${t('adminEventStatus.phase', { phase: t(`adminEvents.phase.${event.phase}`) })}`
            : ''}
        </p>
        <p className="text-sm text-muted-foreground">{t('adminEventStatus.noManualComplete')}</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          disabled={isDisabled || event.status === 'PUBLISHED'}
          aria-current={event.status === 'PUBLISHED' ? 'true' : undefined}
          onClick={() => requestTransition('PUBLISHED')}
        >
          {t('adminEventStatus.actions.publish')}
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={isDisabled || event.status === 'DRAFT'}
          aria-current={event.status === 'DRAFT' ? 'true' : undefined}
          onClick={() => requestTransition('DRAFT')}
        >
          {t('adminEventStatus.actions.draft')}
        </Button>
        <Button
          type="button"
          variant="destructive"
          disabled={isDisabled || event.status === 'CANCELLED'}
          aria-current={event.status === 'CANCELLED' ? 'true' : undefined}
          onClick={() => requestTransition('CANCELLED')}
        >
          {t('adminEventStatus.actions.cancel')}
        </Button>
      </div>

      {showReadiness && missingFields.length > 0 ? (
        <div role="alert" className="rounded-xl border border-destructive/40 bg-destructive/10 p-4">
          <p className="font-semibold text-destructive">{t('adminEventStatus.readiness.title')}</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {missingFields.map((key) => (
              <li key={key}>{t(key)}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {success ? (
        <p role="status" className="text-sm text-emerald-700 dark:text-emerald-300">
          {success}
        </p>
      ) : null}

      <ConfirmDialog
        open={confirmation !== null}
        onOpenChange={(open) => {
          if (!open && !setStatus.isPending) setConfirmation(null)
        }}
        onConfirm={() => {
          if (confirmation) void transition(confirmation)
        }}
        title={t(
          `adminEventStatus.confirm.${confirmation === 'CANCELLED' ? 'cancelTitle' : 'draftTitle'}`,
        )}
        description={t(
          `adminEventStatus.confirm.${confirmation === 'CANCELLED' ? 'cancelDescription' : 'draftDescription'}`,
        )}
        confirmLabel={t(
          `adminEventStatus.actions.${confirmation === 'CANCELLED' ? 'cancel' : 'draft'}`,
        )}
        cancelLabel={t('adminEventStatus.confirm.keep')}
        destructive
        isPending={setStatus.isPending}
        pendingLabel={t('adminEventStatus.saving')}
        error={error}
      />
    </section>
  )
}

export { EventStatusControls }
export type { EventStatusControlsProps }
