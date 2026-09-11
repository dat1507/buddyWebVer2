import { useRef, useState, type FormEvent } from 'react'
import { LockKeyhole, Mail } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { cn } from '@/lib/utils'

type RegistrationField = 'email' | 'password' | 'consent'
type RegistrationErrors = Partial<Record<RegistrationField, string>>

const inputClassName =
  'h-11 w-full rounded-md border border-white/15 bg-black/45 px-10 text-base text-white outline-none transition placeholder:text-zinc-600 hover:border-white/25 focus-visible:border-orange-500 focus-visible:ring-2 focus-visible:ring-orange-500/35'

function UserRegistrationPage() {
  const { t } = useTranslation()
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  const consentRef = useRef<HTMLInputElement>(null)
  const [errors, setErrors] = useState<RegistrationErrors>({})
  const [showBackendNotice, setShowBackendNotice] = useState(false)

  const clearFieldFeedback = (field: RegistrationField) => {
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
    const consentInput = consentRef.current
    const nextErrors: RegistrationErrors = {}

    if (!emailInput?.value.trim()) {
      nextErrors.email = t('auth.register.validation.emailRequired')
    } else if (emailInput.validity.typeMismatch) {
      nextErrors.email = t('auth.register.validation.emailInvalid')
    }

    if (!passwordInput?.value) {
      nextErrors.password = t('auth.register.validation.passwordRequired')
    }

    if (!consentInput?.checked) {
      nextErrors.consent = t('auth.register.validation.consentRequired')
    }

    setErrors(nextErrors)

    const firstInvalidField = (
      [
        ['email', emailInput],
        ['password', passwordInput],
        ['consent', consentInput],
      ] as const
    ).find(([field]) => nextErrors[field])

    if (firstInvalidField) {
      setShowBackendNotice(false)
      firstInvalidField[1]?.focus()
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
            {t('auth.register.eyebrow')}
          </Typography>
          <Typography variant="h1" className="text-3xl sm:text-4xl">
            {t('auth.register.title')}
          </Typography>
          <Typography variant="muted" className="text-base leading-7 text-zinc-400">
            {t('auth.register.subtitle')}
          </Typography>
        </CardHeader>

        <CardContent className="px-5 pb-7 pt-3 sm:px-8 sm:pb-8">
          <form noValidate className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label htmlFor="user-register-email" className="text-sm font-medium text-zinc-200">
                {t('auth.register.emailLabel')}
              </label>
              <div className="relative">
                <Mail
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-500"
                />
                <input
                  ref={emailRef}
                  id="user-register-email"
                  name="email"
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  spellCheck={false}
                  required
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={errors.email ? 'user-register-email-error' : undefined}
                  className={cn(inputClassName, errors.email && 'border-red-500')}
                  placeholder={t('auth.register.emailPlaceholder')}
                  onChange={() => clearFieldFeedback('email')}
                />
              </div>
              {errors.email ? (
                <p id="user-register-email-error" className="text-sm text-red-400">
                  {errors.email}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <label htmlFor="user-register-password" className="text-sm font-medium text-zinc-200">
                {t('auth.register.passwordLabel')}
              </label>
              <div className="relative">
                <LockKeyhole
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-500"
                />
                <input
                  ref={passwordRef}
                  id="user-register-password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={errors.password ? 'user-register-password-error' : undefined}
                  className={cn(inputClassName, errors.password && 'border-red-500')}
                  placeholder={t('auth.register.passwordPlaceholder')}
                  onChange={() => clearFieldFeedback('password')}
                />
              </div>
              {errors.password ? (
                <p id="user-register-password-error" className="text-sm text-red-400">
                  {errors.password}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <div
                className={cn(
                  'flex items-start gap-3 rounded-lg border border-white/10 bg-black/25 p-3',
                  errors.consent && 'border-red-500',
                )}
              >
                <input
                  ref={consentRef}
                  id="user-register-consent"
                  name="consent"
                  type="checkbox"
                  required
                  aria-invalid={Boolean(errors.consent)}
                  aria-describedby={errors.consent ? 'user-register-consent-error' : undefined}
                  className="mt-0.5 size-4 shrink-0 accent-orange-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
                  onChange={() => clearFieldFeedback('consent')}
                />
                <label htmlFor="user-register-consent" className="text-sm leading-5 text-zinc-300">
                  {t('auth.register.consentLabel')}
                </label>
              </div>
              {errors.consent ? (
                <p id="user-register-consent-error" className="text-sm text-red-400">
                  {errors.consent}
                </p>
              ) : null}
            </div>

            <Button type="submit" size="lg" className="w-full">
              {t('auth.register.submit')}
            </Button>

            {showBackendNotice ? (
              <p
                className="rounded-lg border border-orange-500/30 bg-orange-500/10 px-4 py-3 text-sm leading-6 text-orange-100"
                role="status"
              >
                {t('auth.register.backendPending')}
              </p>
            ) : null}
          </form>

          <p className="mt-6 text-center text-sm text-zinc-400">
            {t('auth.register.hasAccount')}{' '}
            <Link
              to="/login"
              className="font-semibold text-orange-400 underline-offset-4 hover:text-orange-300 hover:underline focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
            >
              {t('auth.register.signIn')}
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  )
}

export { UserRegistrationPage }
