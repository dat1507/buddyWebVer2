import { useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { LockKeyhole, Mail } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { cn } from '@/lib/utils'

type LoginField = 'email' | 'password'
type LoginErrors = Partial<Record<LoginField, string>>

const inputClassName =
  'h-11 w-full rounded-md border border-white/15 bg-black/45 px-10 text-base text-white outline-none transition placeholder:text-zinc-600 hover:border-white/25 focus-visible:border-orange-500 focus-visible:ring-2 focus-visible:ring-orange-500/35'

function UserLoginPage() {
  const { t } = useTranslation()
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  const [errors, setErrors] = useState<LoginErrors>({})
  const [showBackendNotice, setShowBackendNotice] = useState(false)

  const clearFieldFeedback = (field: LoginField) => {
    setErrors((currentErrors) => {
      if (!currentErrors[field]) return currentErrors
      return { ...currentErrors, [field]: undefined }
    })
    setShowBackendNotice(false)
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const emailInput = emailRef.current
    const passwordInput = passwordRef.current
    const nextErrors: LoginErrors = {}

    if (!emailInput?.value.trim()) {
      nextErrors.email = t('auth.login.validation.emailRequired')
    } else if (emailInput.validity.typeMismatch) {
      nextErrors.email = t('auth.login.validation.emailInvalid')
    }

    if (!passwordInput?.value) {
      nextErrors.password = t('auth.login.validation.passwordRequired')
    }

    setErrors(nextErrors)

    if (nextErrors.email) {
      setShowBackendNotice(false)
      emailInput?.focus()
      return
    }

    if (nextErrors.password) {
      setShowBackendNotice(false)
      passwordInput?.focus()
      return
    }

    setShowBackendNotice(true)
  }

  return (
    <main className="relative isolate flex min-h-[calc(100svh-4rem)] items-center justify-center overflow-hidden bg-black px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      <div
        className="pointer-events-none absolute left-1/2 top-0 -z-10 h-80 w-80 -translate-x-1/2 rounded-full bg-vgu-orange/20 blur-3xl sm:h-[30rem] sm:w-[30rem]"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute inset-0 -z-20 bg-[radial-gradient(circle_at_top,rgba(255,103,13,0.12),transparent_48%)]"
        aria-hidden="true"
      />

      <Card className="w-full max-w-md border-white/10 bg-zinc-950/90 shadow-2xl backdrop-blur-sm">
        <CardHeader className="space-y-4 px-5 pb-4 pt-7 text-center sm:px-8 sm:pt-8">
          <Typography variant="small" className="uppercase tracking-[0.22em] text-vgu-orange">
            {t('auth.login.eyebrow')}
          </Typography>
          <Typography variant="h1" className="text-3xl sm:text-4xl">
            {t('auth.login.title')}
          </Typography>
          <Typography variant="muted" className="text-base leading-7 text-zinc-400">
            {t('auth.login.subtitle')}
          </Typography>
        </CardHeader>

        <CardContent className="px-5 pb-7 pt-3 sm:px-8 sm:pb-8">
          <form noValidate className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label htmlFor="user-login-email" className="text-sm font-medium text-zinc-200">
                {t('auth.login.emailLabel')}
              </label>
              <div className="relative">
                <Mail
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-500"
                />
                <input
                  ref={emailRef}
                  id="user-login-email"
                  name="email"
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  spellCheck={false}
                  required
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={errors.email ? 'user-login-email-error' : undefined}
                  className={cn(inputClassName, errors.email && 'border-red-500')}
                  placeholder={t('auth.login.emailPlaceholder')}
                  onChange={() => clearFieldFeedback('email')}
                />
              </div>
              {errors.email ? (
                <p id="user-login-email-error" className="text-sm text-red-400">
                  {errors.email}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <label htmlFor="user-login-password" className="text-sm font-medium text-zinc-200">
                {t('auth.login.passwordLabel')}
              </label>
              <div className="relative">
                <LockKeyhole
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-500"
                />
                <input
                  ref={passwordRef}
                  id="user-login-password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={errors.password ? 'user-login-password-error' : undefined}
                  className={cn(inputClassName, errors.password && 'border-red-500')}
                  placeholder={t('auth.login.passwordPlaceholder')}
                  onChange={() => clearFieldFeedback('password')}
                />
              </div>
              {errors.password ? (
                <p id="user-login-password-error" className="text-sm text-red-400">
                  {errors.password}
                </p>
              ) : null}
            </div>

            <Button type="submit" size="lg" className="w-full">
              {t('auth.login.submit')}
            </Button>

            {showBackendNotice ? (
              <p
                className="rounded-lg border border-orange-500/30 bg-orange-500/10 px-4 py-3 text-sm leading-6 text-orange-100"
                role="status"
              >
                {t('auth.login.backendPending')}
              </p>
            ) : null}
          </form>

          <p className="mt-6 text-center text-sm text-zinc-400">
            {t('auth.login.noAccount')}{' '}
            <Link
              to="/register"
              className="font-semibold text-orange-400 underline-offset-4 hover:text-orange-300 hover:underline focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
            >
              {t('auth.login.createAccount')}
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  )
}

export { UserLoginPage }
