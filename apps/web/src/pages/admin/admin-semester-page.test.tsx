import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import {
  adminSemestersClient,
  type SemesterManagementStatus,
} from '@/features/admin-semesters/admin-semesters'
import { adminSemesterKeys } from '@/features/admin-semesters/queries/use-admin-semesters'
import { clearPrivateQueries } from '@/features/auth/private-cache'
import i18n from '@/i18n'
import { useAuthStore } from '@/stores/auth-store'

const admin = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'admin@example.com',
  role: 'ADMIN' as const,
  email_verified: false,
}
const operationId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
const backupId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
const semesterId = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd'
const nextSemesterId = '11111111-1111-4111-8111-111111111111'
const restoreOperationId = 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'
const now = '2026-10-02T08:00:00Z'
const operation = {
  id: operationId,
  operation_type: 'RESET' as const,
  state: 'RUNNING' as const,
  requested_at: now,
  started_at: now,
  completed_at: null,
  failure_code: null,
}
const readyStatus: SemesterManagementStatus = {
  current_semester_id: semesterId,
  current_semester_status: 'CURRENT',
  current_student_accounts_created: 2,
  reset_operation: operation,
  restore_operation: null,
  backup: {
    id: backupId,
    state: 'CREATING',
    created_at: now,
    verified_at: now,
    expires_at: null,
  },
  can_prepare_reset: false,
  can_prepare_restore: false,
  restore_block_reason: 'NEW_COHORT',
}
const resetPreflight = {
  semester_id: semesterId,
  operation_id: operationId,
  backup_id: backupId,
  backup_state: 'CREATING' as const,
  backup_verified: true,
  can_execute: true,
  affected_counts: { users: 2, buddy_messages: 4 },
  preserved_counts: { admins: 1, interests: 8 },
  confirmation_phrase: `RESET ${semesterId}`,
  retention_days: 30 as const,
}
const staleRestorePreflight = {
  operation_id: restoreOperationId,
  backup_id: backupId,
  source_semester_id: semesterId,
  current_semester_id: 'ffffffff-ffff-4fff-8fff-ffffffffffff',
  backup_state: 'READY' as const,
  can_execute: true,
  can_finalize_new_cohort_block: false,
  restored_counts: { users: 3, buddy_messages: 3 },
  avatar_object_count: 3,
  confirmation_phrase: `RESTORE ${backupId}`,
}
const newCohortRestorePreflight = {
  ...staleRestorePreflight,
  backup_state: 'RESTORE_BLOCKED_NEW_DATA' as const,
  can_execute: false,
  can_finalize_new_cohort_block: true,
}
const restoredStatus: SemesterManagementStatus = {
  ...readyStatus,
  current_student_accounts_created: 0,
  reset_operation: {
    ...operation,
    state: 'SUCCEEDED',
    completed_at: now,
  },
  restore_operation: {
    id: restoreOperationId,
    operation_type: 'RESTORE',
    state: 'SUCCEEDED',
    requested_at: now,
    started_at: now,
    completed_at: now,
    failure_code: null,
  },
  backup: {
    id: backupId,
    state: 'READY',
    created_at: now,
    verified_at: now,
    expires_at: '2026-11-01T08:00:00Z',
  },
  restore_block_reason: 'ALREADY_RESTORED',
}
const postResetStatus: SemesterManagementStatus = {
  ...readyStatus,
  current_semester_id: nextSemesterId,
  current_student_accounts_created: 0,
  reset_operation: {
    ...operation,
    state: 'SUCCEEDED',
    completed_at: now,
  },
  backup: {
    id: backupId,
    state: 'READY',
    created_at: now,
    verified_at: now,
    expires_at: '2026-11-01T08:00:00Z',
  },
  can_prepare_reset: true,
  can_prepare_restore: true,
  restore_block_reason: null,
}
const blockedRestoreStatus: SemesterManagementStatus = {
  ...postResetStatus,
  current_student_accounts_created: 1,
  restore_operation: {
    id: restoreOperationId,
    operation_type: 'RESTORE',
    state: 'RUNNING',
    requested_at: now,
    started_at: now,
    completed_at: null,
    failure_code: null,
  },
  can_prepare_reset: false,
  can_prepare_restore: false,
  restore_block_reason: 'NEW_COHORT',
}

describe('SEM-007 Admin Semester Management safety UI', () => {
  let client: QueryClient
  const readStatus = vi.spyOn(adminSemestersClient, 'readStatus')
  const readResetPreflight = vi.spyOn(adminSemestersClient, 'readResetPreflight')
  const readRestorePreflight = vi.spyOn(adminSemestersClient, 'readRestorePreflight')
  const executeReset = vi.spyOn(adminSemestersClient, 'executeReset')
  const executeRestore = vi.spyOn(adminSemestersClient, 'executeRestore')
  const prepareReset = vi.spyOn(adminSemestersClient, 'prepareReset')

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    readStatus.mockReset().mockResolvedValue(readyStatus)
    readResetPreflight.mockReset().mockResolvedValue(resetPreflight)
    readRestorePreflight.mockReset().mockResolvedValue(staleRestorePreflight)
    executeReset.mockReset().mockResolvedValue()
    executeRestore.mockReset().mockResolvedValue()
    prepareReset.mockReset().mockResolvedValue()
  })

  afterEach(() => {
    client.clear()
    useAuthStore.getState().resetSession()
    vi.clearAllMocks()
  })

  function renderPage(role: 'ADMIN' | 'USER' = 'ADMIN') {
    useAuthStore.getState().setAuthenticated({ ...admin, role })
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/admin/semesters']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  it('renders authoritative lifecycle, counts, retention, and non-bypassable block state', async () => {
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Semester management' })).toBeVisible()
    expect(screen.getByText('2 student accounts created in this semester')).toBeVisible()
    expect(await screen.findByText('Chat messages')).toBeVisible()
    expect(screen.getByText('Administrator accounts')).toBeVisible()
    expect(screen.getByText(/permanently blocked/)).toBeVisible()
    expect(screen.queryByRole('button', { name: /override|force/i })).not.toBeInTheDocument()
    expect(screen.getByText(/exactly 30 days/)).toBeVisible()
  })

  it('requires password and exact phrase, submits once, and clears secrets', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Review and execute reset' }))
    const confirm = screen.getByRole('button', { name: 'Execute reset' })
    expect(confirm).toBeDisabled()
    const password = screen.getByLabelText('Current administrator password')
    const phrase = screen.getByLabelText('Type the exact confirmation phrase')
    fireEvent.change(password, { target: { value: 'top-secret' } })
    fireEvent.change(phrase, { target: { value: 'wrong' } })
    expect(confirm).toBeDisabled()
    fireEvent.change(phrase, { target: { value: resetPreflight.confirmation_phrase } })
    fireEvent.click(confirm)
    fireEvent.click(confirm)
    await waitFor(() => expect(executeReset).toHaveBeenCalledTimes(1))
    expect(executeReset).toHaveBeenCalledWith({
      operationId,
      backupId,
      confirmationPhrase: resetPreflight.confirmation_phrase,
      currentPassword: 'top-secret',
    })
    expect(screen.queryByDisplayValue('top-secret')).not.toBeInTheDocument()
    expect(Object.values(localStorage)).not.toContain('top-secret')
    expect(Object.values(localStorage)).not.toContain(resetPreflight.confirmation_phrase)
    expect(Object.values(sessionStorage)).not.toContain('top-secret')
    expect(Object.values(sessionStorage)).not.toContain(resetPreflight.confirmation_phrase)
  })

  it('does not prepare another reset after execute invalidation and authoritative refetch', async () => {
    readStatus.mockReset().mockResolvedValueOnce(readyStatus).mockResolvedValue(postResetStatus)

    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Review and execute reset' }))
    fireEvent.change(screen.getByLabelText('Current administrator password'), {
      target: { value: 'top-secret' },
    })
    fireEvent.change(screen.getByLabelText('Type the exact confirmation phrase'), {
      target: { value: resetPreflight.confirmation_phrase },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Execute reset' }))

    await waitFor(() => expect(executeReset).toHaveBeenCalledTimes(1))
    expect(await screen.findByRole('button', { name: 'Prepare reset and backup' })).toBeVisible()
    expect(readStatus.mock.calls.length).toBeGreaterThanOrEqual(2)
    expect(prepareReset).not.toHaveBeenCalled()
  })

  it('denies USER before any private semester request', async () => {
    renderPage('USER')
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    expect(readStatus).not.toHaveBeenCalled()
  })

  it('keeps lifecycle in the private cache and clears it with session cleanup', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'Semester management' })
    expect(
      client.getQueryCache().findAll({ queryKey: ['private', 'admin-semesters'] }),
    ).not.toHaveLength(0)
    await clearPrivateQueries(client)
    expect(
      client.getQueryCache().findAll({ queryKey: ['private', 'admin-semesters'] }),
    ).toHaveLength(0)
  })

  it('hides cached restore preflight actions after the operation succeeds', async () => {
    readStatus.mockResolvedValue(restoredStatus)
    client.setQueryData(
      adminSemesterKeys.restorePreflight(restoreOperationId),
      staleRestorePreflight,
    )

    renderPage()

    expect(await screen.findByText('This backup has already been restored.')).toBeVisible()
    expect(
      screen.queryByRole('button', { name: 'Review and execute restore' }),
    ).not.toBeInTheDocument()
    expect(readRestorePreflight).not.toHaveBeenCalled()
  })

  it('opens the manual gate only for a server-approved RUNNING new-cohort finalization', async () => {
    readStatus.mockResolvedValue(blockedRestoreStatus)
    readRestorePreflight.mockResolvedValue(newCohortRestorePreflight)
    executeRestore.mockRejectedValue(new Error('RESTORE_BLOCKED_NEW_DATA'))

    renderPage()

    expect(await screen.findByText(/permanently blocked/)).toBeVisible()
    fireEvent.click(await screen.findByRole('button', { name: 'Review and execute restore' }))
    const confirm = screen.getByRole('button', { name: 'Execute restore' })
    expect(confirm).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Current administrator password'), {
      target: { value: 'top-secret' },
    })
    fireEvent.change(screen.getByLabelText('Type the exact confirmation phrase'), {
      target: { value: newCohortRestorePreflight.confirmation_phrase },
    })
    fireEvent.click(confirm)
    fireEvent.click(confirm)

    await waitFor(() => expect(executeRestore).toHaveBeenCalledTimes(1))
    expect(executeRestore).toHaveBeenCalledWith({
      operationId: restoreOperationId,
      backupId,
      confirmationPhrase: newCohortRestorePreflight.confirmation_phrase,
      currentPassword: 'top-secret',
    })
    expect(await screen.findByRole('alert')).toBeVisible()
    expect(screen.queryByDisplayValue('top-secret')).not.toBeInTheDocument()
  })

  it.each([
    ['NEW_COHORT without server approval', 'RESTORE_BLOCKED_NEW_DATA', 'NEW_COHORT'],
    ['an expired backup', 'EXPIRED', 'EXPIRED'],
  ] as const)('does not open the restore gate for %s', async (_label, backupState, reason) => {
    readStatus.mockResolvedValue({ ...blockedRestoreStatus, restore_block_reason: reason })
    readRestorePreflight.mockResolvedValue({
      ...newCohortRestorePreflight,
      backup_state: backupState,
      can_finalize_new_cohort_block: false,
    })

    renderPage()

    await screen.findByText(/Restore returns the exact verified pre-reset dataset/)
    await waitFor(() => expect(readRestorePreflight).toHaveBeenCalledTimes(1))
    expect(
      screen.queryByRole('button', { name: 'Review and execute restore' }),
    ).not.toBeInTheDocument()
    expect(executeRestore).not.toHaveBeenCalled()
  })
})
