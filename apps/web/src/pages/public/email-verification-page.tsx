import { BadgeCheck, CircleAlert, LoaderCircle, MailCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { sessionClient } from '@/features/auth/session-client'
import { useAuthSubmission } from '@/features/auth/use-auth-submission'
import type { ApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/auth-store'

function confirmationError(error: ApiError): string {
  if (error.status === 400) return 'emailVerification.confirm.errors.invalid'
  if (error.status === 429) return 'emailVerification.confirm.errors.rateLimited'
  if (error.status === 401) return 'emailVerification.confirm.errors.session'
  if (error.code === 'network') return 'emailVerification.confirm.errors.network'
  return 'emailVerification.confirm.errors.server'
}

function EmailVerificationPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const tokens = searchParams.getAll('token')
  const token = tokens.length === 1 ? tokens[0]?.trim() : ''
  const status = useAuthStore((state) => state.status)
  const user = useAuthStore((state) => state.user)
  const submission = useAuthSubmission()
  const verified = user?.role === 'USER' && user.email_verified

  const title =
    verified || submission.success
      ? t('emailVerification.confirm.successTitle')
      : t('emailVerification.confirm.title')

  return (
    <main className="flex min-h-[calc(100svh-4rem)] items-center justify-center bg-muted/30 px-4 py-12">
      <Card className="w-full max-w-lg">
        <CardHeader className="space-y-4 text-center">
          <MailCheck className="mx-auto size-10 text-vgu-orange" aria-hidden="true" />
          <Typography variant="small" className="uppercase tracking-[0.2em] text-vgu-orange">
            {t('emailVerification.confirm.eyebrow')}
          </Typography>
          <Typography as="h1" variant="h2">
            {title}
          </Typography>
        </CardHeader>
        <CardContent className="space-y-5 text-center">
          {status === 'unknown' || status === 'loading' ? (
            <div className="flex items-center justify-center gap-2" role="status">
              <LoaderCircle
                className="size-5 animate-spin motion-reduce:animate-none"
                aria-hidden="true"
              />
              <span>{t('emailVerification.confirm.checkingSession')}</span>
            </div>
          ) : !token ? (
            <div className="space-y-2" role="alert">
              <CircleAlert className="mx-auto size-7 text-destructive" aria-hidden="true" />
              <h2 className="font-bold">{t('emailVerification.confirm.missingTitle')}</h2>
              <p className="text-sm leading-6 text-muted-foreground">
                {t('emailVerification.confirm.missing')}
              </p>
            </div>
          ) : status === 'unauthenticated' ? (
            <div className="space-y-4">
              <h2 className="font-bold">{t('emailVerification.confirm.signInTitle')}</h2>
              <p className="text-sm leading-6 text-muted-foreground">
                {t('emailVerification.confirm.signIn')}
              </p>
              <Button asChild>
                <Link to="/login" target="_blank" rel="noreferrer">
                  {t('emailVerification.confirm.signInAction')}
                </Link>
              </Button>
            </div>
          ) : user?.role !== 'USER' ? (
            <div className="space-y-2" role="alert">
              <CircleAlert className="mx-auto size-7 text-destructive" aria-hidden="true" />
              <h2 className="font-bold">{t('emailVerification.confirm.wrongRoleTitle')}</h2>
              <p className="text-sm leading-6 text-muted-foreground">
                {t('emailVerification.confirm.wrongRole')}
              </p>
            </div>
          ) : verified || submission.success ? (
            <div className="space-y-4" role="status">
              <BadgeCheck className="mx-auto size-8 text-emerald-600" aria-hidden="true" />
              <p className="text-sm leading-6 text-muted-foreground">
                {t('emailVerification.confirm.success')}
              </p>
              <Button asChild>
                <Link to="/user">{t('emailVerification.confirm.continue')}</Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm leading-6 text-muted-foreground">
                {t('emailVerification.confirm.description')}
              </p>
              <Button
                type="button"
                disabled={submission.pending}
                onClick={() =>
                  void submission.submit(() => sessionClient.confirmEmailVerification(token))
                }
              >
                {t(
                  submission.pending
                    ? 'emailVerification.confirm.confirming'
                    : 'emailVerification.confirm.submit',
                )}
              </Button>
              {submission.error ? (
                <p
                  className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm"
                  role="alert"
                >
                  {t(confirmationError(submission.error))}
                </p>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  )
}

export { EmailVerificationPage }
