import { LockKeyhole, Mail } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { EmailVerificationStatus } from '@/features/auth/email-verification-status'
import { sessionClient } from '@/features/auth/session-client'
import { useAuthSubmission } from '@/features/auth/use-auth-submission'
import type { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth-store'

type ChangeField = 'email' | 'password'
type ChangeErrors = Partial<Record<ChangeField, string>>

const inputClassName =
  'h-11 w-full rounded-md border border-input bg-background px-10 text-base outline-none transition placeholder:text-muted-foreground focus-visible:border-vgu-orange focus-visible:ring-2 focus-visible:ring-vgu-orange/30 disabled:cursor-not-allowed disabled:opacity-60'

function emailActionError(error: ApiError, change: boolean): string {
  if (change && error.status === 400) return 'emailVerification.settings.errors.password'
  if (change && error.status === 409) return 'emailVerification.settings.errors.conflict'
  if (error.status === 429) return 'emailVerification.settings.errors.rateLimited'
  if (error.status === 401) return 'emailVerification.settings.errors.session'
  if (error.code === 'network') return 'emailVerification.settings.errors.network'
  return 'emailVerification.settings.errors.server'
}

function SettingsPage() {
  const { t } = useTranslation()
  const user = useAuthStore((state) => state.user)
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  const [errors, setErrors] = useState<ChangeErrors>({})
  const verification = useAuthSubmission()
  const change = useAuthSubmission()

  const clearFieldFeedback = (field: ChangeField) => {
    setErrors((current) => (current[field] ? { ...current, [field]: undefined } : current))
    change.clearFeedback()
  }

  const handleChange = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (change.pending) return
    const emailInput = emailRef.current
    const passwordInput = passwordRef.current
    const nextErrors: ChangeErrors = {}

    if (!emailInput?.value.trim()) {
      nextErrors.email = t('emailVerification.settings.validationEmailRequired')
    } else if (emailInput.validity.typeMismatch) {
      nextErrors.email = t('emailVerification.settings.validationEmailInvalid')
    }
    if (!passwordInput?.value) {
      nextErrors.password = t('emailVerification.settings.validationPasswordRequired')
    }
    setErrors(nextErrors)

    if (nextErrors.email) {
      change.clearFeedback()
      emailInput?.focus()
      return
    }
    if (nextErrors.password) {
      change.clearFeedback()
      passwordInput?.focus()
      return
    }

    void change.submit(
      () =>
        sessionClient.changeEmail({
          newEmail: emailInput!.value,
          currentPassword: passwordInput!.value,
        }),
      () => {
        emailInput!.value = ''
        passwordInput!.value = ''
        setErrors({})
      },
    )
  }

  return (
    <section className="min-w-0 space-y-6 py-6" aria-labelledby="settings-title">
      <header className="space-y-2">
        <Typography
          variant="small"
          className="font-semibold uppercase tracking-[0.18em] text-vgu-orange"
        >
          {t('emailVerification.settings.eyebrow')}
        </Typography>
        <Typography as="h1" variant="h2" id="settings-title">
          {t('emailVerification.settings.title')}
        </Typography>
        <Typography variant="muted" className="max-w-2xl text-base leading-7">
          {t('emailVerification.settings.subtitle')}
        </Typography>
      </header>

      <EmailVerificationStatus />

      <Card>
        <CardHeader>
          <CardTitle>{t('emailVerification.settings.verificationTitle')}</CardTitle>
          <CardDescription>
            {t('emailVerification.settings.verificationDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              {t('emailVerification.settings.currentEmail')}
            </p>
            <p className="break-all font-semibold">{user?.email}</p>
          </div>
          {!user?.email_verified ? (
            <Button
              type="button"
              disabled={verification.pending}
              onClick={() => void verification.submit(sessionClient.requestEmailVerification)}
            >
              <Mail aria-hidden="true" />
              {t(
                verification.pending
                  ? 'emailVerification.settings.sending'
                  : 'emailVerification.settings.resend',
              )}
            </Button>
          ) : null}
          {verification.success ? (
            <p
              className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm"
              role="status"
            >
              {t('emailVerification.settings.requested')}
            </p>
          ) : null}
          {verification.error ? (
            <p
              className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm"
              role="alert"
            >
              {t(emailActionError(verification.error, false))}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('emailVerification.settings.changeTitle')}</CardTitle>
          <CardDescription>{t('emailVerification.settings.changeDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          <form noValidate className="space-y-5" aria-busy={change.pending} onSubmit={handleChange}>
            <div className="space-y-2">
              <label htmlFor="settings-new-email" className="text-sm font-medium">
                {t('emailVerification.settings.newEmail')}
              </label>
              <div className="relative">
                <Mail
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                  aria-hidden="true"
                />
                <input
                  ref={emailRef}
                  id="settings-new-email"
                  name="newEmail"
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  required
                  disabled={change.pending}
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={errors.email ? 'settings-new-email-error' : undefined}
                  className={cn(inputClassName, errors.email && 'border-destructive')}
                  placeholder={t('emailVerification.settings.newEmailPlaceholder')}
                  onChange={() => clearFieldFeedback('email')}
                />
              </div>
              {errors.email ? (
                <p id="settings-new-email-error" className="text-sm text-destructive">
                  {errors.email}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <label htmlFor="settings-current-password" className="text-sm font-medium">
                {t('emailVerification.settings.currentPassword')}
              </label>
              <div className="relative">
                <LockKeyhole
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                  aria-hidden="true"
                />
                <input
                  ref={passwordRef}
                  id="settings-current-password"
                  name="currentPassword"
                  type="password"
                  autoComplete="current-password"
                  required
                  disabled={change.pending}
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={errors.password ? 'settings-current-password-error' : undefined}
                  className={cn(inputClassName, errors.password && 'border-destructive')}
                  placeholder={t('emailVerification.settings.currentPasswordPlaceholder')}
                  onChange={() => clearFieldFeedback('password')}
                />
              </div>
              {errors.password ? (
                <p id="settings-current-password-error" className="text-sm text-destructive">
                  {errors.password}
                </p>
              ) : null}
            </div>

            <Button type="submit" disabled={change.pending}>
              {t(
                change.pending
                  ? 'emailVerification.settings.changing'
                  : 'emailVerification.settings.change',
              )}
            </Button>
            {change.success ? (
              <p
                className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm"
                role="status"
              >
                {t('emailVerification.settings.changed')}
              </p>
            ) : null}
            {change.error ? (
              <p
                className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm"
                role="alert"
              >
                {t(emailActionError(change.error, true))}
              </p>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </section>
  )
}

export { SettingsPage }
