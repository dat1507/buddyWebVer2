import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'
import {
  CompatibilityDetails,
  MatchingProfileDetails,
} from '@/features/matching/matching-profile-details'
import { RecommendationAvatar } from '@/features/matching/recommendation-avatar'
import type { Recommendation } from '@/features/matching/recommendation'
import type { CatalogLocale } from '@/features/profile/profile-catalog'
import { useModalIsolation } from '@/hooks/use-modal-isolation'

interface RecommendationProfileDialogProps {
  recommendation: Recommendation | null
  locale: CatalogLocale
  onClose: () => void
}

const focusableSelector = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

function ProfileDetail({ label, value }: { label: string; value: string | null }) {
  const { t } = useTranslation()
  return (
    <div className="min-w-0 rounded-xl border border-border/70 bg-muted/25 p-3">
      <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm font-medium">
        {value || t('recommendedBuddies.profileDialog.notProvided')}
      </dd>
    </div>
  )
}

function RecommendationProfileDialogContent({
  recommendation,
  locale,
  onClose,
}: Omit<RecommendationProfileDialogProps, 'recommendation'> & {
  recommendation: Recommendation
}) {
  const { t } = useTranslation()
  const id = useId()
  const backdropRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const onCloseRef = useRef(onClose)
  const profile = recommendation.profile
  const name = profile.display_name?.trim() || t('recommendedBuddies.unnamed')
  const titleId = `${id}-title`
  const descriptionId = `${id}-description`

  useModalIsolation(backdropRef)

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    const previouslyFocusedElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeButtonRef.current?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onCloseRef.current()
        return
      }
      if (event.key !== 'Tab' || !dialogRef.current) return

      const focusableElements = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(focusableSelector),
      ).filter((element) => element.tabIndex >= 0)
      if (focusableElements.length === 0) {
        event.preventDefault()
        dialogRef.current.focus()
        return
      }

      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]
      const activeElement = document.activeElement
      if (!dialogRef.current.contains(activeElement)) {
        event.preventDefault()
        ;(event.shiftKey ? lastElement : firstElement).focus()
      } else if (event.shiftKey && activeElement === firstElement) {
        event.preventDefault()
        lastElement.focus()
      } else if (!event.shiftKey && activeElement === lastElement) {
        event.preventDefault()
        firstElement.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKeyDown)
      previouslyFocusedElement?.focus()
    }
  }, [])

  return (
    <div
      ref={backdropRef}
      data-testid="recommendation-profile-backdrop"
      className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        tabIndex={-1}
        className="my-auto max-h-[calc(100vh-2rem)] w-full max-w-5xl overflow-y-auto rounded-2xl border border-border bg-card p-5 text-card-foreground shadow-2xl outline-none sm:p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <Typography as="h2" variant="h3" id={titleId} className="break-words">
              {t('recommendedBuddies.profileDialog.title', { name })}
            </Typography>
            <Typography id={descriptionId} variant="muted" className="mt-1">
              {t('recommendedBuddies.profileDialog.description')}
            </Typography>
          </div>
          <Button ref={closeButtonRef} type="button" variant="outline" onClick={onClose}>
            <X aria-hidden="true" />
            {t('recommendedBuddies.profileDialog.close')}
          </Button>
        </div>

        <div className="mt-6 grid min-w-0 gap-6 md:grid-cols-[10rem_minmax(0,1fr)]">
          <RecommendationAvatar profile={profile} />
          <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
            <ProfileDetail label={t('recommendedBuddies.profileDialog.name')} value={name} />
            <ProfileDetail
              label={t('recommendedBuddies.profileDialog.fullName')}
              value={profile.full_name?.trim() || null}
            />
            <ProfileDetail
              label={t('recommendedBuddies.profileDialog.studyProgram')}
              value={profile.major?.trim() || null}
            />
            <ProfileDetail
              label={t('recommendedBuddies.profileDialog.studyYear')}
              value={
                profile.study_year
                  ? t('recommendedBuddies.profileDialog.studyYearValue', {
                      year: profile.study_year,
                    })
                  : null
              }
            />
            <ProfileDetail
              label={t('recommendedBuddies.profileDialog.nationality')}
              value={profile.nationality?.trim() || null}
            />
            <ProfileDetail
              label={t('recommendedBuddies.profileDialog.homeUniversity')}
              value={profile.home_university?.trim() || null}
            />
          </dl>
        </div>

        <section className="mt-6 space-y-2" aria-labelledby={`${id}-about`}>
          <Typography as="h3" variant="h4" id={`${id}-about`}>
            {t('recommendedBuddies.profileDialog.about')}
          </Typography>
          <p className="whitespace-pre-wrap break-words text-sm leading-6 text-muted-foreground">
            {profile.bio?.trim() || t('recommendedBuddies.profileDialog.notProvided')}
          </p>
        </section>

        <div className="mt-6 grid min-w-0 gap-6 lg:grid-cols-2">
          <MatchingProfileDetails profile={profile} />
          <CompatibilityDetails
            explanation={recommendation.explanation}
            locale={locale}
            headingId={`${id}-compatibility`}
          />
        </div>
      </div>
    </div>
  )
}

function RecommendationProfileDialog({
  recommendation,
  locale,
  onClose,
}: RecommendationProfileDialogProps) {
  if (!recommendation || typeof document === 'undefined') return null
  return createPortal(
    <RecommendationProfileDialogContent
      recommendation={recommendation}
      locale={locale}
      onClose={onClose}
    />,
    document.body,
  )
}

export { RecommendationProfileDialog }
