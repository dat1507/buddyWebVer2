import { z } from 'zod'

import { sessionClient } from '@/features/auth/session-client'
import { parseContract } from '@/features/matching/invitation'

const uuid = z.string().uuid()
const timestamp = z.string().datetime({ offset: true })
const operationState = z.enum(['REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED'])
const operationType = z.enum(['RESET', 'RESTORE'])
const backupState = z.enum(['CREATING', 'READY', 'RESTORE_BLOCKED_NEW_DATA', 'EXPIRED', 'FAILED'])
const countMap = z.record(z.string(), z.number().int().nonnegative())

const operationSchema = z
  .object({
    id: uuid,
    operation_type: operationType,
    state: operationState,
    requested_at: timestamp,
    started_at: timestamp.nullable(),
    completed_at: timestamp.nullable(),
    failure_code: z.string().max(100).nullable(),
  })
  .strict()

const backupSchema = z
  .object({
    id: uuid,
    state: backupState,
    created_at: timestamp,
    verified_at: timestamp.nullable(),
    expires_at: timestamp.nullable(),
  })
  .strict()

const semesterManagementStatusSchema = z
  .object({
    current_semester_id: uuid,
    current_semester_status: z.literal('CURRENT'),
    current_student_accounts_created: z.number().int().nonnegative(),
    reset_operation: operationSchema.nullable(),
    restore_operation: operationSchema.nullable(),
    backup: backupSchema.nullable(),
    can_prepare_reset: z.boolean(),
    can_prepare_restore: z.boolean(),
    restore_block_reason: z
      .enum(['NEW_COHORT', 'EXPIRED', 'NOT_READY', 'ALREADY_RESTORED', 'OPERATION_RUNNING'])
      .nullable(),
  })
  .strict()

const preparedSchema = z.object({ operation_id: uuid, backup_id: uuid }).strict()

const resetPreflightSchema = z
  .object({
    semester_id: uuid,
    operation_id: uuid.nullable(),
    backup_id: uuid.nullable(),
    backup_state: backupState.nullable(),
    backup_verified: z.boolean(),
    can_execute: z.boolean(),
    affected_counts: countMap,
    preserved_counts: countMap,
    confirmation_phrase: z.string().min(1).max(64),
    retention_days: z.literal(30),
  })
  .strict()

const restorePreflightSchema = z
  .object({
    operation_id: uuid,
    backup_id: uuid,
    source_semester_id: uuid,
    current_semester_id: uuid,
    backup_state: backupState,
    can_execute: z.boolean(),
    restored_counts: countMap,
    avatar_object_count: z.number().int().nonnegative(),
    confirmation_phrase: z.string().min(1).max(64),
  })
  .strict()

const resetExecuteResponseSchema = z
  .object({
    operation_id: uuid,
    backup_id: uuid,
    closed_semester_id: uuid,
    new_semester_id: uuid,
    deleted_counts: countMap,
    avatar_objects_processed: z.number().int().nonnegative(),
    operation_state: operationState,
    backup_state: backupState,
    idempotent_replay: z.boolean(),
  })
  .strict()

const restoreExecuteResponseSchema = z
  .object({
    operation_id: uuid,
    backup_id: uuid,
    source_semester_id: uuid,
    restored_counts: countMap,
    avatar_objects_restored: z.number().int().nonnegative(),
    operation_state: operationState,
    backup_state: backupState,
    idempotent_replay: z.boolean(),
  })
  .strict()

type SemesterManagementStatus = Readonly<z.infer<typeof semesterManagementStatusSchema>>
type ResetPreflight = Readonly<z.infer<typeof resetPreflightSchema>>
type RestorePreflight = Readonly<z.infer<typeof restorePreflightSchema>>
interface ExecuteInput {
  operationId: string
  backupId: string
  confirmationPhrase: string
  currentPassword: string
}

const adminSemestersClient = {
  async readStatus(signal?: AbortSignal): Promise<SemesterManagementStatus> {
    return parseContract(
      semesterManagementStatusSchema,
      await sessionClient.authenticatedJson('/admin/semesters/management', { signal }),
    )
  },
  async prepareReset(): Promise<void> {
    parseContract(
      preparedSchema,
      await sessionClient.authenticatedJson('/admin/semesters/reset/prepare', { method: 'POST' }),
    )
  },
  async prepareRestore(): Promise<void> {
    parseContract(
      preparedSchema,
      await sessionClient.authenticatedJson('/admin/semesters/restore/prepare', { method: 'POST' }),
    )
  },
  async readResetPreflight(signal?: AbortSignal): Promise<ResetPreflight> {
    return parseContract(
      resetPreflightSchema,
      await sessionClient.authenticatedJson('/admin/semesters/reset/preflight', { signal }),
    )
  },
  async readRestorePreflight(operationId: string, signal?: AbortSignal): Promise<RestorePreflight> {
    return parseContract(
      restorePreflightSchema,
      await sessionClient.authenticatedJson(
        `/admin/semesters/restore/${encodeURIComponent(operationId)}/preflight`,
        { signal },
      ),
    )
  },
  async executeReset(input: ExecuteInput): Promise<void> {
    parseContract(
      resetExecuteResponseSchema,
      await sessionClient.authenticatedJson(
        `/admin/semesters/reset/${encodeURIComponent(input.operationId)}/execute`,
        {
          method: 'POST',
          body: {
            backup_id: input.backupId,
            confirmation_phrase: input.confirmationPhrase,
            current_password: input.currentPassword,
          },
        },
      ),
    )
  },
  async executeRestore(input: ExecuteInput): Promise<void> {
    parseContract(
      restoreExecuteResponseSchema,
      await sessionClient.authenticatedJson(
        `/admin/semesters/restore/${encodeURIComponent(input.operationId)}/execute`,
        {
          method: 'POST',
          body: {
            backup_id: input.backupId,
            confirmation_phrase: input.confirmationPhrase,
            current_password: input.currentPassword,
          },
        },
      ),
    )
  },
}

export {
  adminSemestersClient,
  resetPreflightSchema,
  restorePreflightSchema,
  semesterManagementStatusSchema,
}
export type { ExecuteInput, ResetPreflight, RestorePreflight, SemesterManagementStatus }
