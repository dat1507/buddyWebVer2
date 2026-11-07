import { createContext, useContext } from 'react'
import { z } from 'zod'

import { sessionClient } from '@/features/auth/session-client'
import { getJson } from '@/lib/api'

export const themeIds = ['default', 'halloween', 'christmas', 'summer'] as const
export type ThemeId = (typeof themeIds)[number]

const themeSchema = z.enum(themeIds)
const response = z.object({ theme: themeSchema }).strict()

export const publicThemeKey = ['public-site-theme'] as const
export const themeRefreshMs = 60_000

export function parseThemeId(value: unknown): ThemeId | undefined {
  return themeSchema.safeParse(value).data
}

export const siteThemeClient = {
  async read(signal: AbortSignal) {
    return response.parse(await getJson('/public/site-theme', signal)).theme
  },
  async readAdmin(signal: AbortSignal) {
    return response.parse(await sessionClient.authenticatedJson('/admin/site-theme', { signal }))
      .theme
  },
  async publish(theme: ThemeId) {
    return response.parse(
      await sessionClient.authenticatedJson('/admin/site-theme', {
        method: 'PUT',
        body: { theme },
      }),
    ).theme
  },
}

export const ThemeContext = createContext<ThemeId>('default')

export function useSiteTheme() {
  const theme = useContext(ThemeContext)
  return theme === 'default' ? undefined : theme
}
