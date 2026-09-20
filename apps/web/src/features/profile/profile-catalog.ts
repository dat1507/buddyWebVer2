import { z } from 'zod'

import { ApiError } from '@/lib/api'

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

const profileLanguageSelectionSchema = z.object({
  language_code: languageCodeSchema,
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

const interestSelectionResponseSchema = z.object({
  version: z.number().int().positive(),
  interest_ids: z.array(z.string().uuid()).max(20),
})

const languageSelectionResponseSchema = z.object({
  version: z.number().int().positive(),
  languages: z.array(profileLanguageSelectionSchema).max(10),
})

type CatalogLocale = z.infer<typeof catalogLocaleSchema>
type InterestCatalog = Readonly<z.infer<typeof interestCatalogSchema>>
type LanguageCatalog = Readonly<z.infer<typeof languageCatalogSchema>>
type LanguageProficiency = z.infer<typeof languageProficiencySchema>
type ProfileLanguageSelection = z.infer<typeof profileLanguageSelectionSchema>
type InterestSelectionResponse = Readonly<z.infer<typeof interestSelectionResponseSchema>>
type LanguageSelectionResponse = Readonly<z.infer<typeof languageSelectionResponseSchema>>

interface ProfileSelectionsUpdate {
  version: number
  interestIds: string[]
  languages: ProfileLanguageSelection[]
  updateInterests: boolean
  updateLanguages: boolean
}

interface ProfileSelectionsResult {
  version: number
  interest_ids: string[]
  languages: ProfileLanguageSelection[]
}

function invalidResponse(): never {
  throw new ApiError(200, 'invalidResponse')
}

function hasUniqueValues(values: readonly string[]): boolean {
  return new Set(values).size === values.length
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

function parseInterestSelection(payload: unknown): InterestSelectionResponse {
  const result = interestSelectionResponseSchema.safeParse(payload)
  if (!result.success || !hasUniqueValues(result.data.interest_ids)) return invalidResponse()
  return Object.freeze(result.data)
}

function parseLanguageSelection(payload: unknown): LanguageSelectionResponse {
  const result = languageSelectionResponseSchema.safeParse(payload)
  if (
    !result.success ||
    !hasUniqueValues(result.data.languages.map(({ language_code }) => language_code))
  ) {
    return invalidResponse()
  }
  return Object.freeze(result.data)
}

export {
  catalogLocaleSchema,
  languageProficiencySchema,
  parseInterestCatalog,
  parseInterestSelection,
  parseLanguageCatalog,
  parseLanguageSelection,
  profileLanguageSelectionSchema,
}
export type {
  CatalogLocale,
  InterestCatalog,
  InterestSelectionResponse,
  LanguageCatalog,
  LanguageProficiency,
  LanguageSelectionResponse,
  ProfileLanguageSelection,
  ProfileSelectionsResult,
  ProfileSelectionsUpdate,
}
