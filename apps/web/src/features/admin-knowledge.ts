import { z } from 'zod'

import { sessionClient } from '@/features/auth/session-client'
import { responseSchema } from '@/features/chatbot/chatbot-client'
import { parseContract } from '@/features/matching/invitation'

export const categories = [
  'vgu',
  'buddy-program',
  'student-life',
  'campus-services',
  'transportation',
  'accommodation',
  'buddyweb-guide',
  'faq',
] as const
export const statuses = ['draft', 'published', 'pending', 'unpublished'] as const
export const evidenceTypes = ['unsupported', 'conflicting', 'admin_managed'] as const
const localized = z
  .object({ questions: z.array(z.string().max(500)).max(15), answer: z.string().max(1800) })
  .strict()
const content = z
  .object({
    category: z.enum(categories),
    en: localized,
    de: localized,
    source_title: z.string().max(160),
    source_url: z.string().max(300),
    evidence: z.enum(evidenceTypes),
  })
  .strict()
const revisionNumber = z.number().int().positive()
const faq = z
  .object({
    id: z.uuid(),
    builtin_id: z.string().nullable(),
    version: revisionNumber,
    draft_revision: revisionNumber,
    published_revision: revisionNumber.nullable(),
    published_at: z.iso.datetime({ offset: true }).nullable(),
    updated_at: z.iso.datetime({ offset: true }),
    status: z.enum(statuses),
    content,
  })
  .strict()
const reference = z
  .object({
    id: z.string(),
    category: z.enum(categories),
    status: z.string(),
    content: content.optional(),
    verified_on: z.iso.date().nullable().optional(),
    en: z.string(),
    de: z.string(),
  })
  .strict()
const references = z
  .object({ builtin: z.array(reference).max(200), owner_guide: z.literal('systemPrompt.txt') })
  .strict()
const catalogItem = z
  .object({
    id: z.string(),
    content,
    sources: z.array(z.object({ title: z.string(), reference: z.string() }).strict()),
    status: z.enum(statuses),
    managed: faq.nullable(),
    builtin: reference.nullable(),
  })
  .strict()
export type CatalogItem = z.infer<typeof catalogItem>
// Pinned repository snapshot; this is not an assertion about the running API artifact.
export const systemPromptUrl =
  'https://github.com/dat1507/buddyWebVer2/blob/deef12c0a04cafc2a36c5e7639d2a83301c0bb2c' +
  '/apps/api/app/services/chatbot/sources/systemPrompt.txt'

const history = z
  .object({
    items: z
      .array(
        z
          .object({
            revision: revisionNumber,
            author_id: z.uuid(),
            created_at: z.iso.datetime({ offset: true }),
            content,
          })
          .strict(),
      )
      .max(20),
    has_more: z.boolean(),
  })
  .strict()
const preview = z
  .object({
    question: z.string(),
    answer: responseSchema,
    selected: z.enum(['draft', 'existing', 'fallback']),
    issue: z.string().nullable(),
  })
  .strict()

export type Faq = z.infer<typeof faq>
export type FaqContent = z.infer<typeof content>
export type BuiltinFaq = z.infer<typeof reference>
export type FaqCommand =
  | { action: 'save' }
  | { action: 'publish' | 'unpublish' }
  | { action: 'restore'; revision: number; publish: boolean }

const root = '/admin/knowledge-base'
const path = (id: string) => root + '/' + encodeURIComponent(id)

export const knowledgeClient = {
  async catalog(params: URLSearchParams, signal: AbortSignal) {
    return parseContract(
      z.object({ items: z.array(catalogItem).max(20), has_more: z.boolean() }).strict(),
      await sessionClient.authenticatedJson(root + '/catalog?' + params, { signal }),
    )
  },
  async list(params: URLSearchParams, signal: AbortSignal) {
    return parseContract(
      z.object({ items: z.array(faq).max(20), has_more: z.boolean() }).strict(),
      await sessionClient.authenticatedJson(root + '?' + params, { signal }),
    )
  },
  async references(signal: AbortSignal) {
    return parseContract(
      references,
      await sessionClient.authenticatedJson(root + '/references', { signal }),
    )
  },
  async detail(id: string) {
    return parseContract(faq, await sessionClient.authenticatedJson(path(id)))
  },
  async history(id: string, page: number, signal: AbortSignal) {
    return parseContract(
      history,
      await sessionClient.authenticatedJson(path(id) + '/history?page=' + page, { signal }),
    )
  },
  async save(current: Faq | null, data: FaqContent, builtin_id: string | null) {
    return parseContract(
      faq,
      await sessionClient.authenticatedJson(current ? path(current.id) : root, {
        method: current ? 'PUT' : 'POST',
        body: current ? { version: current.version, content: data } : { builtin_id, content: data },
      }),
    )
  },
  async change(current: Faq, command: Exclude<FaqCommand, { action: 'save' }>) {
    return parseContract(
      faq,
      await sessionClient.authenticatedJson(path(current.id) + '/' + command.action, {
        method: 'POST',
        body: {
          version: current.version,
          confirm: true,
          ...(command.action === 'restore'
            ? { revision: command.revision, publish: command.publish }
            : {}),
        },
      }),
    )
  },
  async preview(
    question: string,
    data: FaqContent,
    faq_id: string | null,
    builtin_id: string | null,
  ) {
    return parseContract(
      preview,
      await sessionClient.authenticatedJson(root + '/preview', {
        method: 'POST',
        body: { question, content: data, faq_id, builtin_id },
      }),
    )
  },
}
