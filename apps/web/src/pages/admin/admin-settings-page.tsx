import { Check, LayoutDashboard, PanelsTopLeft, UserRound } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import {
  publicThemeKey,
  siteThemeClient,
  themeIds,
  type ThemeId,
} from '@/features/site-theme/site-theme'
import { useAuthStore } from '@/stores/auth-store'

const previews = [
  { id: 'landing', Icon: PanelsTopLeft },
  { id: 'login', Icon: UserRound },
  { id: 'dashboard', Icon: LayoutDashboard },
] as const
type PreviewId = (typeof previews)[number]['id']

function ThemeSample({ theme, screen }: { theme: ThemeId; screen: PreviewId }) {
  const { t } = useTranslation()
  return (
    <div className="theme-sample" data-theme-sample={theme} data-preview-screen={screen}>
      <div className="theme-sample-bar">
        <span className="theme-sample-brand">VGU Buddy</span>
        <span>{t('siteTheme.sample.' + screen)}</span>
      </div>
      <div className="theme-sample-content">
        <div>
          <p className="theme-sample-kicker">{t('siteTheme.sample.kicker')}</p>
          <p className="theme-sample-title">{t('siteTheme.sample.' + screen + 'Title')}</p>
          <p className="theme-sample-copy">{t('siteTheme.sample.' + screen + 'Copy')}</p>
          <span className="theme-sample-button">{t('siteTheme.sample.' + screen + 'Action')}</span>
        </div>
        <div className="theme-sample-aside" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  )
}

export function AdminSettingsPage() {
  const { t } = useTranslation()
  const adminId = useAuthStore((state) => state.user?.id)
  const cache = useQueryClient()
  const key = ['private', 'admin-site-theme', adminId] as const
  const current = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => siteThemeClient.readAdmin(signal),
    enabled: Boolean(adminId),
  })
  const [choice, setChoice] = useState<ThemeId>()
  const [screen, setScreen] = useState<PreviewId>('landing')
  const [confirm, setConfirm] = useState(false)
  const selected = choice ?? current.data ?? 'default'
  const mutation = useMutation({
    mutationFn: siteThemeClient.publish,
    onSuccess: (theme) => {
      cache.setQueryData(key, theme)
      cache.setQueryData(publicThemeKey, theme)
      void cache.invalidateQueries({ queryKey: publicThemeKey })
      setConfirm(false)
    },
  })
  const title = (id: ThemeId) => t('siteTheme.presets.' + id + '.name')
  const canPublish = current.isSuccess && selected !== current.data && !mutation.isPending
  return (
    <section className="min-w-0 space-y-5">
      <h1 className="text-2xl font-bold">{t('siteTheme.settings')}</h1>
      <Card className="min-w-0 space-y-5 p-4 sm:p-6">
        <div>
          <h2 className="text-xl font-semibold">{t('siteTheme.title')}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{t('siteTheme.description')}</p>
        </div>
        {current.isPending && <p role="status">{t('siteTheme.loading')}</p>}
        {current.isError && (
          <div className="space-y-2">
            <p role="alert">{t('siteTheme.loadError')}</p>
            <Button variant="outline" onClick={() => void current.refetch()}>
              {t('siteTheme.retry')}
            </Button>
          </div>
        )}
        <div
          role="group"
          aria-label={t('siteTheme.choices')}
          className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
        >
          {themeIds.map((id) => (
            <button
              type="button"
              key={id}
              aria-pressed={selected === id}
              className="min-w-0 rounded-xl border border-border bg-card p-3 text-start focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-pressed:border-primary aria-pressed:ring-1 aria-pressed:ring-primary"
              onClick={() => {
                mutation.reset()
                setChoice(id)
              }}
              disabled={mutation.isPending}
            >
              <span aria-hidden="true" className="theme-mini" data-theme-sample={id}>
                <span />
                <span />
                <span />
              </span>
              <span className="mt-2 flex items-center gap-1 text-sm font-semibold">
                {selected === id && <Check aria-hidden="true" className="size-4 shrink-0" />}
                {title(id)}
              </span>
              <span className="mt-1 block text-sm text-muted-foreground">
                {t('siteTheme.presets.' + id + '.description')}
              </span>
              {current.data === id && (
                <span className="mt-2 block text-xs font-semibold">{t('siteTheme.published')}</span>
              )}
            </button>
          ))}
        </div>
        <p className="text-sm" role="status">
          {current.isSuccess && current.data !== selected
            ? t('siteTheme.unpublished', { theme: title(selected) })
            : current.data && t('siteTheme.active', { theme: title(current.data) })}
        </p>
        <div className="space-y-3">
          <h3 className="text-base font-semibold">{t('siteTheme.preview')}</h3>
          <p className="text-sm text-muted-foreground">{t('siteTheme.previewHint')}</p>
          <div
            role="group"
            aria-label={t('siteTheme.previewPages')}
            className="flex flex-wrap gap-2"
          >
            {previews.map(({ id, Icon }) => (
              <Button
                key={id}
                type="button"
                variant={id === screen ? 'default' : 'outline'}
                aria-pressed={id === screen}
                className="min-h-11"
                onClick={() => setScreen(id)}
              >
                <Icon aria-hidden="true" />
                {t('siteTheme.sample.' + id)}
              </Button>
            ))}
          </div>
          <ThemeSample theme={selected} screen={screen} />
        </div>
        <Button
          onClick={() => {
            mutation.reset()
            setConfirm(true)
          }}
          disabled={!canPublish}
        >
          {t('siteTheme.publish')}
        </Button>
        {mutation.isSuccess && (
          <p role="status">{t('siteTheme.success', { theme: title(mutation.data) })}</p>
        )}
      </Card>
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        onConfirm={() => {
          if (canPublish) mutation.mutate(selected)
        }}
        title={t('siteTheme.confirmTitle')}
        description={t('siteTheme.confirmDescription', { theme: title(selected) })}
        confirmLabel={t('siteTheme.publish')}
        cancelLabel={t('siteTheme.cancel')}
        isPending={mutation.isPending}
        pendingLabel={t('siteTheme.publishing')}
        error={mutation.isError ? t('siteTheme.publishError') : undefined}
      />
    </section>
  )
}
