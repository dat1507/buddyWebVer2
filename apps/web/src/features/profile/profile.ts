import { z } from 'zod'

import { profileLanguageSelectionSchema } from '@/features/profile/profile-catalog'
import { profilePhotoSchema } from '@/features/profile/profile-photo'
import { ApiError } from '@/lib/api'

const studentTypeSchema = z.enum(['VIETNAMESE', 'INTERNATIONAL'])

const weeklyAvailabilitySlotSchema = z.object({
  weekday: z.number().int().min(1).max(7),
  start_minute: z.number().int().min(0).max(1439),
  end_minute: z.number().int().min(0).max(1440),
})

const weeklyAvailabilitySchema = z.object({
  timezone: z.string().min(1).max(64),
  slots: z.array(weeklyAvailabilitySlotSchema).max(100),
})

const profilePreferencesSchema = z.object({
  preferred_activity_ids: z.array(z.string().uuid()).max(20),
})

const ownProfileSchema = z.object({
  id: z.string().uuid(),
  full_name: z.string().nullable(),
  display_name: z.string().nullable(),
  student_type: studentTypeSchema.nullable(),
  nationality: z.string().nullable(),
  major: z.string().nullable(),
  study_year: z.number().int().min(1).max(10).nullable(),
  bio: z.string().nullable(),
  home_university: z.string().nullable().default(null),
  arrival_date: z.string().nullable().default(null),
  departure_date: z.string().nullable().default(null),
  availability: weeklyAvailabilitySchema.nullable().default(null),
  preferences: profilePreferencesSchema.nullable().default(null),
  matching_opt_in: z.boolean().default(false),
  avatar: profilePhotoSchema.nullable().default(null),
  interest_ids: z.array(z.string().uuid()).max(20).default([]),
  languages: z.array(profileLanguageSelectionSchema).max(10).default([]),
  version: z.number().int().positive(),
})

type OwnProfile = Readonly<z.infer<typeof ownProfileSchema>>
type ProfilePreferences = Readonly<z.infer<typeof profilePreferencesSchema>>
type StudentType = z.infer<typeof studentTypeSchema>
type WeeklyAvailability = Readonly<z.infer<typeof weeklyAvailabilitySchema>>
type WeeklyAvailabilitySlot = Readonly<z.infer<typeof weeklyAvailabilitySlotSchema>>

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

interface OnboardingPreferencesUpdate {
  version: number
  availability: WeeklyAvailability | null
  preferences: ProfilePreferences
  matching_opt_in: boolean
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
export type {
  OnboardingPreferencesUpdate,
  OwnProfile,
  OwnProfileUpdate,
  ProfilePreferences,
  StudentType,
  WeeklyAvailability,
  WeeklyAvailabilitySlot,
}
