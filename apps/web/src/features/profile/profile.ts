import { z } from 'zod'

import { profileLanguageSelectionSchema } from '@/features/profile/profile-catalog'
import { ApiError } from '@/lib/api'

const studentTypeSchema = z.enum(['VIETNAMESE', 'INTERNATIONAL'])

const ownProfileSchema = z.object({
  id: z.string().uuid(),
  full_name: z.string().nullable(),
  display_name: z.string().nullable(),
  student_type: studentTypeSchema.nullable(),
  nationality: z.string().nullable(),
  major: z.string().nullable(),
  study_year: z.number().int().min(1).max(10).nullable(),
  bio: z.string().nullable(),
  interest_ids: z.array(z.string().uuid()).max(20).default([]),
  languages: z.array(profileLanguageSelectionSchema).max(10).default([]),
  version: z.number().int().positive(),
})

type OwnProfile = Readonly<z.infer<typeof ownProfileSchema>>
type StudentType = z.infer<typeof studentTypeSchema>

interface OwnProfileUpdate {
  version: number
  full_name: string
  display_name: string | null
  student_type: StudentType
  nationality: string | null
  major: string | null
  study_year: number | null
  bio: string | null
}

function parseOwnProfile(payload: unknown): OwnProfile {
  try {
    const result = ownProfileSchema.safeParse(payload)
    if (result.success) return Object.freeze(result.data)
  } catch {
    // Do not retain validation diagnostics derived from a private response.
  }
  throw new ApiError(200, 'invalidResponse')
}

export { parseOwnProfile, studentTypeSchema }
export type { OwnProfile, OwnProfileUpdate, StudentType }
