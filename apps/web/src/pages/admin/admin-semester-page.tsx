import { useId, useState } from 'react'
import { AlertTriangle, ArchiveRestore, CalendarClock, DatabaseBackup } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Typography } from '@/components/ui/typography'
import type {
  ResetPreflight,
  RestorePreflight,
  SemesterManagementStatus,
} from '@/features/admin-semesters/admin-semesters'
import {
  useExecuteReset,
  useExecuteRestore,
  usePrepareReset,
  usePrepareRestore,
  useResetPreflight,
  useRestorePreflight,
  useSemesterStatus,
} from '@/features/admin-semesters/queries/use-admin-semesters'

type ActionKind = 'reset' | 'restore'
const inputClass =
  'h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50'
const countKeys = [
  'users',
  'student_profiles',
  'profile_custom_preferences',
  'matching_invitations',
  'matches',
  'buddy_conversations',
  'buddy_messages',
  'profile_photos',
  'admins',
  'interests',
  'languages',
  'activities',
  'events',
  'semester_backups',
] as const

function formatDate(value: string | null, locale: string, unavailable: string): string {
  if (!value) return unavailable
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  )
}

function StatusBadge({ state }: { state: string }) {
  const { t } = useTranslation()
  return (
    <span className="inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold">
      {t(`adminSemester.states.${state}`)}
    </span>
  )
}

function Counts({ title, counts }: { title: string; counts: Record<string, number> }) {
  const { t } = useTranslation()
  const entries = countKeys.flatMap((key) => (key in counts ? [[key, counts[key]] as const] : []))
  return (
    <section className="space-y-2">
      <h4 className="font-semibold">{title}</h4>
      <dl className="grid gap-2 sm:grid-cols-2">
        {entries.map(([key, count]) => (
          <div key={key} className="flex justify-between gap-3 rounded-lg border px-3 py-2 text-sm">
            <dt>{t(`adminSemester.counts.${key}`)}</dt>
            <dd className="font-semibold tabular-nums">{count}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function LifecycleOverview({ status }: { status: SemesterManagementStatus }) {
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage ?? 'en'
  const unavailable = t('adminSemester.unavailable')
  return (
    <div className="grid min-w-0 gap-4 lg:grid-cols-3">
      <Card className="min-w-0 shadow-none">
        <CardHeader>
          <CardTitle className="text-lg">{t('adminSemester.current.title')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="break-all font-mono text-xs">{status.current_semester_id}</p>
          <StatusBadge state={status.current_semester_status} />
          <p>
            {t('adminSemester.current.students', {
              count: status.current_student_accounts_created,
            })}
          </p>
        </CardContent>
      </Card>
      <Card className="min-w-0 shadow-none">
        <CardHeader>
          <CardTitle className="text-lg">{t('adminSemester.operations.title')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          {(['reset', 'restore'] as const).map((kind) => {
            const operation = status[`${kind}_operation`]
            return (
              <div key={kind} className="space-y-1 rounded-lg border p-3">
                <p className="font-semibold">{t(`adminSemester.operations.${kind}`)}</p>
                {operation ? (
                  <>
                    <StatusBadge state={operation.state} />
                    <p>{formatDate(operation.started_at, locale, unavailable)}</p>
                  </>
                ) : (
                  <p className="text-muted-foreground">{unavailable}</p>
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>
      <Card className="min-w-0 shadow-none">
        <CardHeader>
          <CardTitle className="text-lg">{t('adminSemester.backup.title')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {status.backup ? (
            <>
              <StatusBadge state={status.backup.state} />
              <p>{t('adminSemester.backup.created')}</p>
              <p>{formatDate(status.backup.created_at, locale, unavailable)}</p>
              <p>{t('adminSemester.backup.expires')}</p>
              <p>{formatDate(status.backup.expires_at, locale, unavailable)}</p>
            </>
          ) : (
            <p className="text-muted-foreground">{unavailable}</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function ConfirmationFields({
  kind,
  phrase,
  password,
  confirmation,
  onPassword,
  onConfirmation,
}: {
  kind: ActionKind
  phrase: string
  password: string
  confirmation: string
  onPassword: (value: string) => void
  onConfirmation: (value: string) => void
}) {
  const { t } = useTranslation()
  const id = useId()
  return (
    <div className="mt-4 space-y-4 text-foreground">
      <p className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 font-semibold">
        {t(`adminSemester.${kind}.warning`)}
      </p>
      <div className="space-y-1">
        <label htmlFor={`${id}-password`} className="font-medium">
          {t('adminSemester.dialog.password')}
        </label>
        <input
          id={`${id}-password`}
          className={inputClass}
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => onPassword(event.target.value)}
        />
      </div>
      <div className="space-y-1">
        <label htmlFor={`${id}-phrase`} className="font-medium">
          {t('adminSemester.dialog.confirmation')}
        </label>
        <p id={`${id}-help`} className="break-all font-mono text-xs">
          {phrase}
        </p>
        <input
          id={`${id}-phrase`}
          aria-describedby={`${id}-help`}
          className={inputClass}
          autoComplete="off"
          value={confirmation}
          onChange={(event) => onConfirmation(event.target.value)}
        />
      </div>
    </div>
  )
}

function AdminSemesterPage() {
  const { t } = useTranslation()
  const titleId = useId()
  const status = useSemesterStatus()
  const resetRunning = status.data?.reset_operation?.state === 'RUNNING'
  const restoreId = status.data?.restore_operation?.id ?? null
  const restoreRunning = status.data?.restore_operation?.state === 'RUNNING'
  const resetPreflight = useResetPreflight(resetRunning)
  const restorePreflight = useRestorePreflight(restoreId, restoreRunning)
  const prepareReset = usePrepareReset()
  const prepareRestore = usePrepareRestore()
  const executeReset = useExecuteReset()
  const executeRestore = useExecuteRestore()
  const [dialog, setDialog] = useState<ActionKind | null>(null)
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [feedback, setFeedback] = useState<'success' | 'error' | null>(null)

  const resetSensitiveState = () => {
    setPassword('')
    setConfirmation('')
  }
  const closeDialog = () => {
    setDialog(null)
    resetSensitiveState()
  }
  const currentPreflight: ResetPreflight | RestorePreflight | undefined =
    dialog === 'reset' ? resetPreflight.data : restorePreflight.data
  const mutation = dialog === 'reset' ? executeReset : executeRestore
  const phrase = currentPreflight?.confirmation_phrase ?? ''
  const canSubmit = Boolean(
    currentPreflight?.can_execute && password && confirmation === phrase && !mutation.isPending,
  )
  const execute = async () => {
    if (!dialog || !currentPreflight || !canSubmit) return
    setFeedback(null)
    try {
      await mutation.mutateAsync({
        operationId: currentPreflight.operation_id!,
        backupId: currentPreflight.backup_id!,
        confirmationPhrase: confirmation,
        currentPassword: password,
      })
      setFeedback('success')
      closeDialog()
      await status.refetch()
    } catch {
      setFeedback('error')
      resetSensitiveState()
    }
  }

  if (status.isPending) return <p role="status">{t('adminSemester.loading')}</p>
  if (status.isError)
    return (
      <div className="space-y-3 py-6">
        <p role="alert">{t('adminSemester.loadError')}</p>
        <Button type="button" variant="outline" onClick={() => void status.refetch()}>
          {t('adminSemester.retry')}
        </Button>
      </div>
    )

  const data = status.data
  const blocked = data.restore_block_reason
  return (
    <section aria-labelledby={titleId} className="min-w-0 space-y-8 py-6">
      <header className="space-y-2">
        <Typography as="h1" variant="h2" id={titleId}>
          {t('adminSemester.title')}
        </Typography>
        <Typography variant="lead" className="max-w-3xl">
          {t('adminSemester.description')}
        </Typography>
      </header>
      {feedback ? (
        <p role={feedback === 'error' ? 'alert' : 'status'} className="rounded-lg border p-3">
          {t(`adminSemester.feedback.${feedback}`)}
        </p>
      ) : null}
      <LifecycleOverview status={data} />

      <div className="grid min-w-0 gap-6 xl:grid-cols-2">
        <Card className="min-w-0 border-destructive/30 shadow-none">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DatabaseBackup aria-hidden="true" /> {t('adminSemester.reset.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p>{t('adminSemester.reset.description')}</p>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              <li>{t('adminSemester.reset.removed')}</li>
              <li>{t('adminSemester.reset.adminPreserved')}</li>
              <li>{t('adminSemester.reset.catalogsPreserved')}</li>
              <li>{t('adminSemester.reset.retention')}</li>
            </ul>
            {resetPreflight.data ? (
              <>
                <Counts
                  title={t('adminSemester.reset.deletedCounts')}
                  counts={resetPreflight.data.affected_counts}
                />
                <Counts
                  title={t('adminSemester.reset.preservedCounts')}
                  counts={resetPreflight.data.preserved_counts}
                />
              </>
            ) : null}
            {resetRunning && resetPreflight.isPending ? (
              <p role="status">{t('adminSemester.preflightLoading')}</p>
            ) : null}
            {resetRunning && resetPreflight.data && !resetPreflight.data.can_execute ? (
              <p role="status">{t('adminSemester.preparing')}</p>
            ) : null}
            <div className="flex flex-wrap gap-3">
              {data.can_prepare_reset ? (
                <Button
                  type="button"
                  variant="outline"
                  disabled={prepareReset.isPending}
                  onClick={() => void prepareReset.mutateAsync().catch(() => setFeedback('error'))}
                >
                  {prepareReset.isPending
                    ? t('adminSemester.preparing')
                    : t('adminSemester.reset.prepare')}
                </Button>
              ) : null}
              {resetPreflight.data?.can_execute ? (
                <Button type="button" variant="destructive" onClick={() => setDialog('reset')}>
                  {t('adminSemester.reset.open')}
                </Button>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <Card className="min-w-0 shadow-none">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ArchiveRestore aria-hidden="true" /> {t('adminSemester.restore.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p>{t('adminSemester.restore.description')}</p>
            {blocked ? (
              <div role="status" className="flex gap-2 rounded-lg border border-amber-500/50 p-3">
                <AlertTriangle aria-hidden="true" className="mt-0.5 shrink-0" />
                <p>{t(`adminSemester.restore.blockReasons.${blocked}`)}</p>
              </div>
            ) : null}
            {restorePreflight.data ? (
              <Counts
                title={t('adminSemester.restore.restoredCounts')}
                counts={restorePreflight.data.restored_counts}
              />
            ) : null}
            <div className="flex flex-wrap gap-3">
              {data.can_prepare_restore && !restoreRunning ? (
                <Button
                  type="button"
                  variant="outline"
                  disabled={prepareRestore.isPending}
                  onClick={() =>
                    void prepareRestore.mutateAsync().catch(() => setFeedback('error'))
                  }
                >
                  {prepareRestore.isPending
                    ? t('adminSemester.preparing')
                    : t('adminSemester.restore.prepare')}
                </Button>
              ) : null}
              {restorePreflight.data?.can_execute ? (
                <Button type="button" variant="destructive" onClick={() => setDialog('restore')}>
                  {t('adminSemester.restore.open')}
                </Button>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </div>

      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <CalendarClock aria-hidden="true" className="size-4" />
        {t('adminSemester.authoritative')}
      </p>
      <ConfirmDialog
        open={dialog !== null}
        onOpenChange={(open) => {
          if (!open) closeDialog()
        }}
        onConfirm={() => void execute()}
        title={t(`adminSemester.${dialog ?? 'reset'}.dialogTitle`)}
        description={
          <ConfirmationFields
            kind={dialog ?? 'reset'}
            phrase={phrase}
            password={password}
            confirmation={confirmation}
            onPassword={setPassword}
            onConfirmation={setConfirmation}
          />
        }
        confirmLabel={t(`adminSemester.${dialog ?? 'reset'}.confirm`)}
        pendingLabel={t('adminSemester.running')}
        cancelLabel={t('adminSemester.dialog.cancel')}
        destructive
        confirmDisabled={!canSubmit}
        isPending={mutation.isPending}
        error={mutation.isError ? t('adminSemester.feedback.error') : undefined}
      />
    </section>
  )
}

export { AdminSemesterPage }
