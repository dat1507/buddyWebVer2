import type { ReactNode } from 'react'
import { LoaderCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Navigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useProfileCompletion } from '@/features/profile/queries/use-own-profile'

type ProfileReadinessRequirement = 'complete' | 'incomplete' | 'matchingEligible'

interface ProfileReadinessGateProps {
  children: ReactNode
  requirement: ProfileReadinessRequirement
}

function ProfileReadinessGate({ children, requirement }: ProfileReadinessGateProps) {
  const { t } = useTranslation()
  const completion = useProfileCompletion()

  if (completion.isPending) {
    return (
      <section
        className="flex min-h-72 items-center justify-center gap-3 py-6 text-muted-foreground"
        aria-busy="true"
      >
        <LoaderCircle
          className="size-5 animate-spin motion-reduce:animate-none"
          aria-hidden="true"
        />
        <span role="status">{t('profileReadiness.loading')}</span>
      </section>
    )
  }

  if (completion.isError) {
    return (
      <section className="py-6" aria-labelledby="profile-readiness-error-title">
        <Card className="mx-auto max-w-2xl border-destructive/40">
          <CardHeader>
            <CardTitle id="profile-readiness-error-title">
              {t('profileReadiness.errorTitle')}
            </CardTitle>
            <CardDescription role="alert">{t('profileReadiness.error')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" onClick={() => void completion.refetch()}>
              {t('profileReadiness.retry')}
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }

  if (requirement === 'incomplete') {
    return completion.data.status === 'COMPLETE' ? (
      <Navigate to="/user/profile/edit" replace />
    ) : (
      children
    )
  }

  if (completion.data.status === 'INCOMPLETE') {
    return <Navigate to="/user/onboarding" replace />
  }

  if (requirement === 'matchingEligible' && !completion.data.matching_eligible) {
    return <Navigate to="/user/profile/edit" replace />
  }

  return children
}

export { ProfileReadinessGate }
export type { ProfileReadinessRequirement }
