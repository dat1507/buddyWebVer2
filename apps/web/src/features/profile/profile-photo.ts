import { z } from 'zod'

import { ApiError } from '@/lib/api'

const profilePhotoSchema = z.object({
  id: z.string().uuid(),
  mime_type: z.enum(['image/jpeg', 'image/png', 'image/webp']),
  byte_size: z.number().int().positive(),
  width: z.number().int().positive().max(4096),
  height: z.number().int().positive().max(4096),
  processing_status: z.enum(['READY', 'FAILED']),
  created_at: z.string().datetime({ offset: true }),
})

const profilePhotoUrlSchema = z.object({
  id: z.string().uuid(),
  url: z.string().url(),
  expires_in: z.number().int().min(1).max(300),
})

type ProfilePhoto = Readonly<z.infer<typeof profilePhotoSchema>>
type ProfilePhotoUrl = Readonly<z.infer<typeof profilePhotoUrlSchema> & { expiresAt: number }>

function parseProfilePhotoUrl(payload: unknown, photoId: string): ProfilePhotoUrl {
  const result = profilePhotoUrlSchema.safeParse(payload)
  if (
    !result.success ||
    result.data.id !== photoId ||
    !/^https?:$/i.test(new URL(result.data.url).protocol)
  ) {
    throw new ApiError(200, 'invalidResponse')
  }
  return Object.freeze({
    ...result.data,
    expiresAt: Date.now() + result.data.expires_in * 1_000,
  })
}

export { parseProfilePhotoUrl, profilePhotoSchema }
export type { ProfilePhoto, ProfilePhotoUrl }
