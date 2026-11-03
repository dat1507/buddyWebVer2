import { z } from 'zod'
import { sessionClient } from '@/features/auth/session-client'
import { parseContract } from '@/features/matching/invitation'
import { requestJson } from '@/lib/api'

export const photoSchema = z.object({
  id: z.string().uuid(),
  alt_en: z.string(),
  alt_de: z.string(),
  caption_en: z.string().nullable(),
  caption_de: z.string().nullable(),
  width: z.number().int().positive(),
  height: z.number().int().positive(),
  sort_order: z.number().int().nonnegative(),
})
export const recapSchema = z.object({
  id: z.string().uuid(),
  related_event_id: z.string().uuid().nullable(),
  title_en: z.string().nullable(),
  title_de: z.string().nullable(),
  summary_en: z.string().nullable(),
  summary_de: z.string().nullable(),
  editorial_en: z.string().nullable(),
  editorial_de: z.string().nullable(),
  event_date: z.string().nullable(),
  status: z.enum(['DRAFT', 'PUBLISHED', 'ARCHIVED']),
  version: z.number().int().positive(),
  thumbnail_id: z.string().uuid().nullable(),
  photos: z.array(photoSchema).max(12),
  cleanup_pending: z.boolean(),
})
export const recapListSchema = z.object({
  items: z.array(recapSchema),
  page: z.number(),
  total: z.number(),
  total_pages: z.number(),
  years: z.array(z.number()),
  mosaic: z.array(recapSchema).max(5),
  pending_cleanup: z.array(z.string().uuid()).default([]),
})
export type RecapPhoto = z.infer<typeof photoSchema>
export type Recap = z.infer<typeof recapSchema>
export type RecapList = z.infer<typeof recapListSchema>
export const isUuid = (id: string | undefined): id is string => z.uuid().safeParse(id).success
export const localized = (value: { [key: string]: unknown }, field: string, de: boolean) =>
  String(value[`${field}_${de ? 'de' : 'en'}`] || value[`${field}_${de ? 'en' : 'de'}`] || '')

export async function fetchRecaps(page: number, year: string, admin = false, signal?: AbortSignal) {
  const path = `${admin ? '/admin' : ''}/recaps?page=${page}${year ? `&year=${encodeURIComponent(year)}` : ''}`
  return parseContract(
    recapListSchema,
    await (admin
      ? sessionClient.authenticatedJson(path, { signal })
      : requestJson(path, { signal })),
  )
}
export async function fetchRecap(id: string, admin = false, signal?: AbortSignal) {
  const path = `${admin ? '/admin' : ''}/recaps/${id}`
  return parseContract(
    recapSchema,
    await (admin
      ? sessionClient.authenticatedJson(path, { signal })
      : requestJson(path, { signal })),
  )
}
export async function mutateRecap(path: string, method: 'POST' | 'PUT' | 'PATCH', body: unknown) {
  return parseContract(
    recapSchema,
    await sessionClient.authenticatedJson(`/admin/recaps${path}`, { method, body }),
  )
}

// Bound simultaneous URL-signing requests; images themselves remain browser-lazy loaded.
let active = 0
const queue: (() => void)[] = []
export async function photoUrl(
  recapId: string,
  photoId: string,
  display: boolean,
  admin: boolean,
  signal?: AbortSignal,
) {
  if (active >= 3) await new Promise<void>((resolve) => queue.push(resolve))
  active++
  try {
    const path = `${admin ? '/admin' : ''}/recaps/${recapId}/photos/${photoId}/url?variant=${display ? 'display' : 'thumbnail'}`
    const payload = admin
      ? await sessionClient.authenticatedJson(path, { signal })
      : await requestJson(path, { signal })
    return parseContract(
      z.object({
        url: z.url().startsWith('https://'),
        expires_in: z.number().int().min(1).max(300),
      }),
      payload,
    )
  } finally {
    active--
    queue.shift()?.()
  }
}
