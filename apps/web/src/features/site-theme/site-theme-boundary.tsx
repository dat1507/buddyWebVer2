import { useEffect, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useLocation } from 'react-router'

import { queryClient } from '@/lib/query-client'
import {
  parseThemeId,
  publicThemeKey,
  siteThemeClient,
  themeRefreshMs,
  ThemeContext,
} from './site-theme'

const previewKey = 'buddyweb-local-theme-preview'

function readLocalPreview(search: string) {
  if (
    !import.meta.env.DEV ||
    import.meta.env.VITE_SEASONAL_PREVIEW !== 'true' ||
    !['localhost', '127.0.0.1'].includes(window.location.hostname)
  ) {
    return { command: null, theme: undefined }
  }

  const command = new URLSearchParams(search).get('theme-preview')
  if (command === 'live') return { command, theme: undefined }
  const requested = parseThemeId(command)
  if (requested) return { command, theme: requested }
  try {
    return { command: null, theme: parseThemeId(window.sessionStorage.getItem(previewKey)) }
  } catch {
    return { command: null, theme: undefined }
  }
}

export function SiteThemeBoundary({ children }: { children: ReactNode }) {
  const { search } = useLocation()
  const preview = readLocalPreview(search)
  useEffect(() => {
    if (!import.meta.env.DEV) return
    try {
      if (preview.command === 'live') window.sessionStorage.removeItem(previewKey)
      else if (preview.command && preview.theme)
        window.sessionStorage.setItem(previewKey, preview.theme)
    } catch {
      // The current URL can still preview a preset when storage is unavailable.
    }
  }, [preview.command, preview.theme])

  const published = useQuery(
    {
      queryKey: publicThemeKey,
      queryFn: ({ signal }) => siteThemeClient.read(signal),
      enabled: preview.theme === undefined,
      retry: false,
      staleTime: themeRefreshMs,
      refetchInterval: themeRefreshMs,
      refetchIntervalInBackground: false,
      refetchOnWindowFocus: 'always',
    },
    queryClient,
  )
  const theme = preview.theme ?? (published.isError ? 'default' : (published.data ?? 'default'))
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>
}
