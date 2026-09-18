import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { sessionClient } from '@/features/auth/session-client'
import { useAuthStore } from '@/stores/auth-store'

function SessionBootstrap() {
  useEffect(() => {
    void sessionClient.bootstrap().catch(() => undefined)
  }, [])
  return null
}

function SessionControls() {
  const { t } = useTranslation()
  const status = useAuthStore((state) => state.status)
  const { pending, action, error } = sessionClient.useFeedback()
  const retry = () => {
    const work = action === 'logout' ? sessionClient.logout() : sessionClient.bootstrap()
    void work.catch(() => undefined)
  }
  // Form-local login errors already have their own feedback and submit-again retry.
  const sessionError = error && action !== 'login'
  if (action === 'login' && status !== 'authenticated') return null
  if (!pending && !sessionError && status !== 'authenticated') return null
  return (
    <aside
      aria-label={t('auth.session.label')}
      className="border-b border-white/10 bg-zinc-950 px-4 py-3 text-sm text-zinc-200"
    >
      {pending && action !== 'login' ? <p role="status">{t('auth.session.pending')}</p> : null}
      {sessionError ? (
        <div role="alert" className="flex flex-wrap items-center gap-3">
          <p>{t(`auth.errors.${error.code}`)}</p>
          <Button type="button" variant="outline" disabled={pending} onClick={retry}>
            {t('auth.session.retry')}
          </Button>
        </div>
      ) : null}
      {status === 'authenticated' ? (
        <Button
          type="button"
          variant="outline"
          disabled={pending}
          onClick={() => void sessionClient.logout().catch(() => undefined)}
        >
          {t('auth.session.logout')}
        </Button>
      ) : null}
    </aside>
  )
}

export { SessionBootstrap, SessionControls }
