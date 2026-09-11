import { useRef, useState, type FormEvent } from 'react'
import { LockKeyhole, Mail, ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { cn } from '@/lib/utils'

type AdminLoginField = 'email' | 'password'
type AdminLoginErrors = Partial<Record<AdminLoginField, string>>

const inputClassName =
  'h-11 w-full rounded-md border border-amber-300/20 bg-black/50 px-10 text-base text-white outline-none transition placeholder:text-zinc-600 hover:border-amber-300/35 focus-visible:border-amber-400 focus-visible:ring-2 focus-visible:ring-amber-400/35'

function AdminLoginPage() {
  const { t } = useTranslation()
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  const [errors, setErrors] = useState<AdminLoginErrors>({})
  const [showBackendNotice, setShowBackendNotice] = useState(false)

  const clearFieldFeedback = (field: AdminLoginField) => {
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
    const nextErrors: AdminLoginErrors = {}

    if (!emailInput?.value.trim()) {
      nextErrors.email = t('auth.adminLogin.validation.emailRequired')
    } else if (emailInput.validity.typeMismatch) {
      nextErrors.email = t('auth.adminLogin.validation.emailInvalid')
    }

    if (!passwordInput?.value) {
      nextErrors.password = t('auth.adminLogin.validation.passwordRequired')
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
    <main
      className="relative isolate flex min-h-[calc(100svh-4rem)] items-center justify-center overflow-hidden bg-zinc-950 px-4 py-12 sm:px-6 sm:py-16 lg:px-8"
      data-auth-surface="admin"
    >
      <div
        className="pointer-events-none absolute inset-0 -z-20 bg-[linear-gradient(rgba(251,191,36,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(251,191,36,0.035)_1px,transparent_1px)] bg-[size:2rem_2rem]"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[28rem] w-[28rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-500/10 blur-3xl"
        aria-hidden="true"
      />

      <Card className="grid w-full max-w-5xl overflow-hidden border-amber-300/20 bg-black/90 shadow-2xl shadow-amber-950/30 md:grid-cols-2">
        <section className="flex min-w-0 flex-col justify-between overflow-hidden border-b border-amber-300/15 bg-amber-400/[0.06] p-6 md:border-b-0 md:border-r md:p-8">
          <div>
            <div className="flex size-12 items-center justify-center rounded-xl border border-amber-300/25 bg-amber-400/10 text-amber-300">
              <ShieldCheck aria-hidden="true" className="size-6" />
            </div>
            <Typography variant="small" className="mt-6 uppercase tracking-[0.2em] text-amber-300">
              {t('auth.adminLogin.eyebrow')}
            </Typography>
            <Typography variant="h1" className="mt-3 text-2xl sm:text-3xl lg:text-4xl">
              {t('auth.adminLogin.title')}
            </Typography>
            <Typography variant="muted" className="mt-4 text-base leading-7 text-zinc-400">
              {t('auth.adminLogin.subtitle')}
            </Typography>
          </div>

          <p className="mt-8 rounded-lg border border-amber-300/15 bg-black/35 p-4 text-sm leading-6 text-zinc-400">
            {t('auth.adminLogin.provisioningNote')}
          </p>
        </section>

        <div className="min-w-0">
          <CardHeader className="space-y-2 px-5 pb-4 pt-7 sm:px-8 sm:pt-8">
            <Typography variant="h2" className="text-2xl">
              {t('auth.adminLogin.formTitle')}
            </Typography>
            <Typography variant="muted" className="text-sm leading-6 text-zinc-400">
              {t('auth.adminLogin.formDescription')}
            </Typography>
          </CardHeader>

          <CardContent className="px-5 pb-7 pt-3 sm:px-8 sm:pb-8">
            <form noValidate className="space-y-5" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <label htmlFor="admin-login-email" className="text-sm font-medium text-zinc-200">
                  {t('auth.adminLogin.emailLabel')}
                </label>
                <div className="relative">
                  <Mail
                    aria-hidden="true"
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-500"
                  />
                  <input
                    ref={emailRef}
                    id="admin-login-email"
                    name="email"
                    type="email"
                    inputMode="email"
                    autoComplete="username"
                    spellCheck={false}
                    required
                    aria-invalid={Boolean(errors.email)}
                    aria-describedby={errors.email ? 'admin-login-email-error' : undefined}
                    className={cn(inputClassName, errors.email && 'border-red-500')}
                    placeholder={t('auth.adminLogin.emailPlaceholder')}
                    onChange={() => clearFieldFeedback('email')}
                  />
                </div>
                {errors.email ? (
                  <p id="admin-login-email-error" className="text-sm text-red-400">
                    {errors.email}
                  </p>
                ) : null}
              </div>

              <div className="space-y-2">
                <label htmlFor="admin-login-password" className="text-sm font-medium text-zinc-200">
                  {t('auth.adminLogin.passwordLabel')}
                </label>
                <div className="relative">
                  <LockKeyhole
                    aria-hidden="true"
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-500"
                  />
                  <input
                    ref={passwordRef}
                    id="admin-login-password"
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    aria-invalid={Boolean(errors.password)}
                    aria-describedby={errors.password ? 'admin-login-password-error' : undefined}
                    className={cn(inputClassName, errors.password && 'border-red-500')}
                    placeholder={t('auth.adminLogin.passwordPlaceholder')}
                    onChange={() => clearFieldFeedback('password')}
                  />
                </div>
                {errors.password ? (
                  <p id="admin-login-password-error" className="text-sm text-red-400">
                    {errors.password}
                  </p>
                ) : null}
              </div>

              <Button
                type="submit"
                size="lg"
                className="w-full bg-amber-400 text-black hover:bg-amber-300 focus-visible:ring-amber-400"
              >
                {t('auth.adminLogin.submit')}
              </Button>

              {showBackendNotice ? (
                <p
                  className="rounded-lg border border-amber-300/25 bg-amber-400/10 px-4 py-3 text-sm leading-6 text-amber-100"
                  role="status"
                >
                  {t('auth.adminLogin.backendPending')}
                </p>
              ) : null}
            </form>
          </CardContent>
        </div>
      </Card>
    </main>
  )
}

export { AdminLoginPage }
