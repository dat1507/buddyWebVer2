import { BadgeCheck, CircleAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth-store'

function EmailVerificationStatus({ manage = false }: { manage?: boolean }) {
  const { t } = useTranslation()
  const user = useAuthStore((state) => state.user)
  if (!user || user.role !== 'USER') return null

  const verified = user.email_verified
  const Icon = verified ? BadgeCheck : CircleAlert

  return (
    <div
      role="status"
      aria-label={t('emailVerification.status.label')}
      className={cn(
        'flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-center sm:justify-between',
        verified
          ? 'border-emerald-500/30 bg-emerald-500/10'
          : 'border-amber-500/35 bg-amber-500/10',
      )}
    >
      <div className="flex items-start gap-3">
        <Icon
          className={cn('mt-0.5 size-5 shrink-0', verified ? 'text-emerald-600' : 'text-amber-600')}
          aria-hidden="true"
        />
        <div>
          <p className="font-semibold">
            {t(`emailVerification.status.${verified ? 'verified' : 'unverified'}`)}
          </p>
          <p className="text-sm leading-6 text-muted-foreground">
            {t(
              `emailVerification.status.${verified ? 'verifiedDescription' : 'unverifiedDescription'}`,
            )}
          </p>
        </div>
      </div>
      {manage ? (
        <Button asChild variant="outline" size="sm" className="shrink-0">
          <Link to="/user/settings">{t('emailVerification.status.manage')}</Link>
        </Button>
      ) : null}
    </div>
  )
}

export { EmailVerificationStatus }
