import { z } from 'zod'

import { ApiError } from '@/lib/api'

const RECOMMENDATION_PAGE_SIZE = 20

const isoDateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .refine((value) => {
    const parsed = new Date(`${value}T00:00:00.000Z`)
    return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(value)
  })

const preferenceSchema = z
  .object({
    id: z.string().uuid().nullable(),
    code: z.string().nullable(),
    label: z.string().min(1).max(120),
    is_custom: z.boolean(),
  })
  .strict()
  .refine(({ id, code, is_custom }) =>
    is_custom ? id === null && code === null : id !== null && code !== null,
  )

const languageSchema = z
  .object({
    code: z.string().nullable(),
    label: z.string().min(1).max(120),
    proficiency: z.enum(['native', 'fluent', 'intermediate', 'beginner']),
    is_custom: z.boolean(),
  })
  .strict()
  .refine(({ code, is_custom }) => (is_custom ? code === null : code !== null))

const availabilitySlotSchema = z
  .object({
    weekday: z.number().int().min(1).max(7),
    start_minute: z.number().int().min(0).max(1439),
    end_minute: z.number().int().min(1).max(1440),
  })
  .strict()
  .refine(({ start_minute, end_minute }) => end_minute > start_minute)

const weeklyAvailabilitySchema = z
  .object({
    timezone: z.string().min(1).max(64),
    slots: z.array(availabilitySlotSchema).max(100),
  })
  .strict()

const safeMatchingProfileSchema = z
  .object({
    id: z.string().uuid(),
    display_name: z.string().max(80).nullable(),
    student_type: z.enum(['VIETNAMESE', 'INTERNATIONAL']),
    major: z.string().nullable(),
    avatar: z
      .object({
        id: z.string().uuid(),
        width: z.number().int().positive(),
        height: z.number().int().positive(),
      })
      .strict(),
    interests: z.array(preferenceSchema).min(1).max(20),
    languages: z.array(languageSchema).min(1).max(10),
    activities: z.array(preferenceSchema).max(20),
    availability: weeklyAvailabilitySchema.nullable(),
  })
  .strict()

const compatibilitySignalSchema = z
  .object({
    similarity: z.number().min(0).max(1),
    weight: z.number().int().min(0).max(100),
    points: z.number().min(0).max(100),
  })
  .strict()
  .refine(({ points, weight }) => points <= weight)

const compatibilityWeights = {
  interests: 40,
  activities: 35,
  availability: 15,
  languages: 5,
  major: 5,
} as const

const compatibilityExplanationSchema = z
  .object({
    interests: compatibilitySignalSchema,
    activities: compatibilitySignalSchema,
    availability: compatibilitySignalSchema,
    languages: compatibilitySignalSchema,
    major: compatibilitySignalSchema,
  })
  .strict()
  .superRefine((value, context) => {
    for (const [signal, weight] of Object.entries(compatibilityWeights)) {
      if (value[signal as keyof typeof compatibilityWeights].weight !== weight) {
        context.addIssue({
          code: 'custom',
          message: 'Unexpected compatibility weight.',
          path: [signal, 'weight'],
        })
      }
    }
  })

const recommendationSchema = z
  .object({
    profile: safeMatchingProfileSchema,
    score: z.number().int().min(0).max(100),
    explanation: compatibilityExplanationSchema,
  })
  .strict()

const recommendationListSchema = z
  .object({
    items: z.array(recommendationSchema),
    page: z.number().int().min(1),
    page_size: z.number().int().min(1).max(50),
    total: z.number().int().min(0),
    total_pages: z.number().int().min(0),
    reference_week_start: isoDateSchema,
  })
  .strict()
  .superRefine((value, context) => {
    const expectedPages = value.total === 0 ? 0 : Math.ceil(value.total / value.page_size)
    if (value.items.length > value.page_size || value.total_pages !== expectedPages) {
      context.addIssue({ code: 'custom', message: 'Inconsistent recommendation pagination.' })
    }
    const profileIds = value.items.map(({ profile }) => profile.id)
    if (new Set(profileIds).size !== profileIds.length) {
      context.addIssue({ code: 'custom', message: 'Duplicate recommendation profile.' })
    }
  })

type MatchingPreference = Readonly<z.infer<typeof preferenceSchema>>
type MatchingLanguage = Readonly<z.infer<typeof languageSchema>>
type MatchingAvailability = Readonly<z.infer<typeof weeklyAvailabilitySchema>>
type MatchingProfile = Readonly<z.infer<typeof safeMatchingProfileSchema>>
type CompatibilityExplanation = Readonly<z.infer<typeof compatibilityExplanationSchema>>
type CompatibilitySignal = Readonly<z.infer<typeof compatibilitySignalSchema>>
type Recommendation = Readonly<z.infer<typeof recommendationSchema>>
type RecommendationList = Readonly<z.infer<typeof recommendationListSchema>>

function parseRecommendationList(payload: unknown): RecommendationList {
  try {
    const result = recommendationListSchema.safeParse(payload)
    if (result.success) return Object.freeze(result.data)
  } catch {
    // Validation details can contain private response values; expose only the stable API error.
  }
  throw new ApiError(200, 'invalidResponse')
}

export { RECOMMENDATION_PAGE_SIZE, parseRecommendationList }
export type {
  CompatibilityExplanation,
  CompatibilitySignal,
  MatchingAvailability,
  MatchingLanguage,
  MatchingPreference,
  MatchingProfile,
  Recommendation,
  RecommendationList,
}
