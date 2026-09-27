import { z } from 'zod'

import { preferenceComparisonKey } from '@/features/profile/preference-normalization'
import { ApiError } from '@/lib/api'

const MAX_INTERESTS = 20
const MAX_LANGUAGES = 10
const MAX_ACTIVITIES = 20

const catalogLocaleSchema = z.enum(['en', 'de'])
const languageProficiencySchema = z.enum(['native', 'fluent', 'intermediate', 'beginner'])
const languageCodeSchema = z
  .string()
  .min(2)
  .max(35)
  .regex(/^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$/)

const interestCatalogItemSchema = z.object({
  id: z.string().uuid(),
  code: z.string().min(1).max(64),
  label: z.string().min(1).max(120),
  category: z.string().min(1).max(80),
})

const languageCatalogItemSchema = z.object({
  code: languageCodeSchema,
  label: z.string().min(1).max(120),
})

const activityCatalogItemSchema = z.object({
  id: z.string().uuid(),
  code: z.string().min(1).max(64),
  label: z.string().min(1).max(120),
})

const profileLanguageSelectionSchema = z.object({
  language_code: languageCodeSchema,
  proficiency: languageProficiencySchema,
})

const customPreferenceSelectionSchema = z.object({
  label: z.string().min(1).max(120),
})

const customLanguageSelectionSchema = customPreferenceSelectionSchema.extend({
  proficiency: languageProficiencySchema,
})

const interestCatalogSchema = z.object({
  locale: catalogLocaleSchema,
  items: z.array(interestCatalogItemSchema),
})

const languageCatalogSchema = z.object({
  locale: catalogLocaleSchema,
  items: z.array(languageCatalogItemSchema),
})

const activityCatalogSchema = z.object({
  locale: catalogLocaleSchema,
  items: z.array(activityCatalogItemSchema),
})

const profilePreferenceSnapshotSchema = z
  .object({
    version: z.number().int().positive(),
    interest_ids: z.array(z.string().uuid()).max(MAX_INTERESTS),
    custom_interests: z.array(customPreferenceSelectionSchema).max(MAX_INTERESTS),
    languages: z.array(profileLanguageSelectionSchema).max(MAX_LANGUAGES),
    custom_languages: z.array(customLanguageSelectionSchema).max(MAX_LANGUAGES),
    activity_ids: z.array(z.string().uuid()).max(MAX_ACTIVITIES),
    custom_activities: z.array(customPreferenceSelectionSchema).max(MAX_ACTIVITIES),
  })
  .refine(
    ({ interest_ids, custom_interests }) =>
      interest_ids.length + custom_interests.length <= MAX_INTERESTS,
  )
  .refine(
    ({ languages, custom_languages }) =>
      languages.length + custom_languages.length <= MAX_LANGUAGES,
  )
  .refine(
    ({ activity_ids, custom_activities }) =>
      activity_ids.length + custom_activities.length <= MAX_ACTIVITIES,
  )

type CatalogLocale = z.infer<typeof catalogLocaleSchema>
type InterestCatalog = Readonly<z.infer<typeof interestCatalogSchema>>
type LanguageCatalog = Readonly<z.infer<typeof languageCatalogSchema>>
type ActivityCatalog = Readonly<z.infer<typeof activityCatalogSchema>>
type LanguageProficiency = z.infer<typeof languageProficiencySchema>
type ProfileLanguageSelection = z.infer<typeof profileLanguageSelectionSchema>
type CustomPreferenceSelection = z.infer<typeof customPreferenceSelectionSchema>
type CustomLanguageSelection = z.infer<typeof customLanguageSelectionSchema>
type ProfilePreferenceSnapshot = Readonly<z.infer<typeof profilePreferenceSnapshotSchema>>
type ProfilePreferenceUpdate = z.input<typeof profilePreferenceSnapshotSchema>

function invalidResponse(): never {
  throw new ApiError(200, 'invalidResponse')
}

function hasUniqueValues(values: readonly string[]): boolean {
  return new Set(values).size === values.length
}

function hasUniqueCustomLabels(values: readonly CustomPreferenceSelection[]): boolean {
  const keys = values.map(({ label }) => preferenceComparisonKey(label))
  return keys.every(Boolean) && new Set(keys).size === keys.length
}

function parseInterestCatalog(payload: unknown, locale: CatalogLocale): InterestCatalog {
  const result = interestCatalogSchema.safeParse(payload)
  if (
    !result.success ||
    result.data.locale !== locale ||
    !hasUniqueValues(result.data.items.map(({ id }) => id)) ||
    !hasUniqueValues(result.data.items.map(({ code }) => code))
  ) {
    return invalidResponse()
  }
  return Object.freeze(result.data)
}

function parseLanguageCatalog(payload: unknown, locale: CatalogLocale): LanguageCatalog {
  const result = languageCatalogSchema.safeParse(payload)
  if (
    !result.success ||
    result.data.locale !== locale ||
    !hasUniqueValues(result.data.items.map(({ code }) => code))
  ) {
    return invalidResponse()
  }
  return Object.freeze(result.data)
}

function parseActivityCatalog(payload: unknown, locale: CatalogLocale): ActivityCatalog {
  const result = activityCatalogSchema.safeParse(payload)
  if (
    !result.success ||
    result.data.locale !== locale ||
    !hasUniqueValues(result.data.items.map(({ id }) => id)) ||
    !hasUniqueValues(result.data.items.map(({ code }) => code))
  ) {
    return invalidResponse()
  }
  return Object.freeze(result.data)
}

function parseProfilePreferenceSnapshot(payload: unknown): ProfilePreferenceSnapshot {
  const result = profilePreferenceSnapshotSchema.safeParse(payload)
  if (
    !result.success ||
    !hasUniqueValues(result.data.interest_ids) ||
    !hasUniqueValues(result.data.activity_ids) ||
    !hasUniqueValues(result.data.languages.map(({ language_code }) => language_code)) ||
    !hasUniqueCustomLabels(result.data.custom_interests) ||
    !hasUniqueCustomLabels(result.data.custom_languages) ||
    !hasUniqueCustomLabels(result.data.custom_activities)
  ) {
    return invalidResponse()
  }
  return Object.freeze(result.data)
}

export {
  MAX_ACTIVITIES,
  MAX_INTERESTS,
  MAX_LANGUAGES,
  catalogLocaleSchema,
  languageProficiencySchema,
  parseActivityCatalog,
  parseInterestCatalog,
  parseLanguageCatalog,
  parseProfilePreferenceSnapshot,
  profileLanguageSelectionSchema,
}
export type {
  ActivityCatalog,
  CatalogLocale,
  CustomLanguageSelection,
  CustomPreferenceSelection,
  InterestCatalog,
  LanguageCatalog,
  LanguageProficiency,
  ProfileLanguageSelection,
  ProfilePreferenceSnapshot,
  ProfilePreferenceUpdate,
}
