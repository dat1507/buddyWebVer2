import { z } from 'zod'

import { ApiError, requestJson } from '@/lib/api'

const codePoints = (text: string) => [...text].length
const validQuestion = (text: string) =>
  text.trim().length > 0 &&
  codePoints(text) <= 500 &&
  [...text].every(
    (character) => character.charCodeAt(0) >= 32 || character === '\n' || character === '\t',
  )

// Match the backend's public URL family; no arbitrary response string becomes a link.
function publicSourceUrl(value: string) {
  try {
    const url = new URL(value)
    return (
      value.startsWith('https://') &&
      url.protocol === 'https:' &&
      (url.hostname === 'vgu.edu.vn' || url.hostname.endsWith('.vgu.edu.vn')) &&
      (!url.port || url.port === '443') &&
      !url.username &&
      !url.password &&
      !url.search &&
      !url.hash &&
      !/\s/.test(value) &&
      !value.includes('\\') &&
      [...value].every((character) => character.charCodeAt(0) >= 32)
    )
  } catch {
    return false
  }
}

const responseSchema = z
  .object({
    answer: z
      .string()
      .min(1)
      .refine((value) => codePoints(value) <= 1800),
    language: z.enum(['en', 'de', 'und']),
    supported: z.boolean(),
    status: z.enum([
      'answer',
      'historical_reference',
      'owner_provided',
      'conflicted',
      'clarification',
      'insufficient',
      'choose_language',
      'restricted',
    ]),
    mode: z.literal('local_retrieval'),
    sources: z
      .array(
        z
          .object({
            entry_id: z.string().regex(/^[a-z][a-z0-9-]{2,79}$/),
            title: z.enum([
              'BuddyWeb guide',
              'VGU public information',
              'Historical student guide (systemPrompt.txt)',
              'Owner-provided guide (systemPrompt.txt)',
            ]),
            verification_status: z.enum([
              'verified_code',
              'verified_official',
              'historical_reference',
              'owner_provided',
              'conflicted',
            ]),
            verified_on: z.iso.date().nullable(),
            provenance: z
              .object({
                filename: z.literal('systemPrompt.txt'),
                sha256: z.string().regex(/^[a-f0-9]{64}$/),
                start_line: z.number().int().positive(),
                end_line: z.number().int().positive(),
                section: z.string().min(1).max(160),
              })
              .strict()
              .refine((value) => value.end_line >= value.start_line)
              .optional(),
            references: z
              .array(
                z
                  .object({
                    title: z.string().min(1).max(160),
                    url: z.string().min(1).max(300).refine(publicSourceUrl),
                  })
                  .strict(),
              )
              .max(5),
          })
          .strict(),
      )
      .max(3),
  })
  .strict()
  .refine(
    (value) =>
      value.supported === Boolean(value.sources.length) &&
      (['answer', 'historical_reference', 'owner_provided', 'conflicted'].includes(value.status)
        ? value.supported
        : !value.supported) &&
      (value.status === 'conflicted') ===
        value.sources.some((source) => source.verification_status === 'conflicted') &&
      (value.status === 'owner_provided') ===
        (!value.sources.some((source) => source.verification_status === 'conflicted') &&
          value.sources.some((source) => source.verification_status === 'owner_provided')) &&
      (value.status === 'historical_reference') ===
        (!value.sources.some((source) =>
          ['owner_provided', 'conflicted'].includes(source.verification_status),
        ) &&
          value.sources.some((source) => source.verification_status === 'historical_reference')) &&
      value.sources.every(
        (source) =>
          (source.verification_status !== 'verified_official' || source.references.length > 0) &&
          (['owner_provided', 'conflicted'].includes(source.verification_status)
            ? source.verified_on === null &&
              source.title === 'Owner-provided guide (systemPrompt.txt)' &&
              source.references.length === 0 &&
              /^owner-[a-f0-9]{20}$/.test(source.entry_id) &&
              Boolean(source.provenance)
            : source.provenance === undefined &&
              (source.verification_status === 'historical_reference'
                ? source.verified_on === null &&
                  source.title === 'Historical student guide (systemPrompt.txt)' &&
                  source.references.length === 0 &&
                  ['legacy-d9-food', 'legacy-laundry'].includes(source.entry_id)
                : source.verified_on !== null &&
                  source.title ===
                    (source.verification_status === 'verified_code'
                      ? 'BuddyWeb guide'
                      : 'VGU public information'))),
      ),
  )

type ChatbotAnswer = z.infer<typeof responseSchema>

const chatbotClient = {
  async ask(question: string, signal?: AbortSignal): Promise<ChatbotAnswer> {
    if (!validQuestion(question)) throw new ApiError(422, 'validation')
    const payload = await requestJson('/chatbot/query', {
      method: 'POST',
      body: { question },
      signal,
    })
    const parsed = responseSchema.safeParse(payload)
    if (!parsed.success) throw new ApiError(0, 'invalidResponse')
    return parsed.data
  },
}

export { chatbotClient, codePoints, validQuestion }
export type { ChatbotAnswer }
