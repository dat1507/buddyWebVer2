/// <reference types="node" />

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import {
  incomingInvitationListSchema,
  parseContract,
  validateInvitationMessage,
} from '@/features/matching/invitation'
import { ApiError } from '@/lib/api'
import { incomingInvitationList } from '@/test/invitations'

interface LiteralCase {
  name: string
  input: string
  canonical: string
  word_count: number
  code_point_count: number
  reason: string | null
}

interface GeneratedCase {
  name: string
  unit: string
  separator: string
  repeat: number
  word_count: number
  code_point_count: number
  reason: string | null
}

interface InvitationMessageContract {
  limits: { max_words: number; max_code_points: number }
  literal_cases: LiteralCase[]
  generated_cases: GeneratedCase[]
}

const contract = JSON.parse(
  readFileSync(
    resolve(process.cwd(), '..', '..', 'contracts', 'invitation_message_validation.json'),
    'utf8',
  ),
) as InvitationMessageContract

describe('INV-007 invitation contracts', () => {
  it.each(contract.literal_cases)('matches shared literal vector $name', (testCase) => {
    expect(validateInvitationMessage(testCase.input)).toEqual({
      canonical: testCase.canonical,
      wordCount: testCase.word_count,
      codePointCount: testCase.code_point_count,
      reason: testCase.reason,
    })
  })

  it.each(contract.generated_cases)('matches shared boundary vector $name', (testCase) => {
    const message = Array(testCase.repeat).fill(testCase.unit).join(testCase.separator)
    expect(validateInvitationMessage(message)).toEqual({
      canonical: message.trim(),
      wordCount: testCase.word_count,
      codePointCount: testCase.code_point_count,
      reason: testCase.reason,
    })
  })

  it('counts supplementary emoji as one Unicode code point instead of UTF-16 units', () => {
    expect('😀'.length).toBe(2)
    expect(validateInvitationMessage('😀'.repeat(10_000))).toMatchObject({
      codePointCount: 10_000,
      reason: null,
    })
  })

  it.each(['email', 'user_id', 'normalized_key', 'storage_path'])(
    'rejects private or internal response field %s',
    (privateField) => {
      const payload = structuredClone(incomingInvitationList) as Record<string, unknown>
      const items = payload.items as Array<Record<string, unknown>>
      const sender = items[0].sender as Record<string, unknown>
      sender[privateField] = 'private-value'
      expect(() => parseContract(incomingInvitationListSchema, payload)).toThrow(ApiError)
    },
  )
})
