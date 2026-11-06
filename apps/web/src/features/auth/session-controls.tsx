import { useEffect } from 'react'
import { LogOut } from 'lucide-react'
import { useLocation } from 'react-router'
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

function LogoutAction({ className, onLogout }: { className?: string; onLogout?: () => void }) {
  const { t } = useTranslation()
  const { pending } = sessionClient.useFeedback()
  return (
    <Button
      type="button"
      variant="ghost"
      className={className}
      disabled={pending}
      onClick={() => {
        void sessionClient.logout().catch(() => undefined)
        onLogout?.()
      }}
    >
      <LogOut aria-hidden="true" className="size-4" />
      {t('auth.session.logout')}
    </Button>
  )
}

function SessionControls() {
  const { pathname } = useLocation()
  const publicShell = !/^\/(user|admin)(\/|$)/.test(pathname)
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
  if (!pending && !sessionError && (publicShell || status !== 'authenticated')) return null
  return (
    <aside
      aria-label={t('auth.session.label')}
      className={
        publicShell
          ? 'session-controls fixed bottom-4 left-4 z-[60] max-w-[calc(100vw-2rem)] rounded-xl border border-white/10 bg-zinc-950 px-4 py-3 text-sm text-zinc-200 shadow-lg'
          : 'session-controls border-b border-white/10 bg-zinc-950 px-4 py-3 text-sm text-zinc-200'
      }
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
      {!publicShell && status === 'authenticated' ? (
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

export { LogoutAction, SessionBootstrap, SessionControls }
