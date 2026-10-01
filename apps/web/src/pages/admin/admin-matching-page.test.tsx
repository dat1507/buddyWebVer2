import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import {
  adminMatchingClient,
  type AdminMatchingParticipantList,
} from '@/features/admin-matching/admin-matching'
import { clearPrivateQueries } from '@/features/auth/private-cache'
import i18n from '@/i18n'
import { useAuthStore } from '@/stores/auth-store'

const admin = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'admin@example.com',
  role: 'ADMIN',
  email_verified: false,
}
const profileId = '11111111-1111-4111-8111-111111111111'
const stats = {
  participant_count: 45,
  verified_participant_count: 31,
  active_match_count: 14,
  zero_buddy_participant_count: 8,
  invitations: { pending: 6, accepted: 17, declined: 4, cancelled: 3, expired: 2 },
}
const participant = {
  profile_id: profileId,
  display_name: 'Linh Nguyen',
  student_type: 'VIETNAMESE' as const,
  is_active: true,
  email_verified: true,
  matching_opt_in: true,
  buddy_count: 2,
}
const detail = {
  profile: {
    id: profileId,
    display_name: 'Linh Nguyen',
    student_type: 'VIETNAMESE' as const,
    major: 'Computer Science',
    avatar: null,
    interests: [
      {
        id: '22222222-2222-4222-8222-222222222222',
        code: 'photography',
        label: 'Photography',
        is_custom: false,
      },
    ],
    languages: [{ code: null, label: 'Thai', proficiency: 'fluent' as const, is_custom: true }],
    activities: [{ id: null, code: null, label: 'Formula 1', is_custom: true }],
    availability: null,
  },
  is_active: true,
  email_verified: true,
  matching_opt_in: true,
  buddy_count: 2,
}

function participantPage(page = 1, pageSize = 20, total = 45): AdminMatchingParticipantList {
  return {
    items: total ? [participant] : [],
    page,
    page_size: pageSize,
    total,
    total_pages: total ? Math.ceil(total / pageSize) : 0,
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

describe('ADMIN-V2-002 guarded matching monitoring UI', () => {
  let client: QueryClient
  const readStats = vi.spyOn(adminMatchingClient, 'readStats')
  const readParticipants = vi.spyOn(adminMatchingClient, 'readParticipants')
  const readParticipantDetail = vi.spyOn(adminMatchingClient, 'readParticipantDetail')

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    readStats.mockReset().mockResolvedValue(stats)
    readParticipants
      .mockReset()
      .mockImplementation(async ({ page, pageSize }) => participantPage(page, pageSize))
    readParticipantDetail.mockReset().mockResolvedValue(detail)
  })

  afterEach(() => {
    client.clear()
    useAuthStore.getState().resetSession()
    vi.clearAllMocks()
  })

  const renderApp = (role: 'ADMIN' | 'USER' = 'ADMIN') => {
    useAuthStore.getState().setAuthenticated({ ...admin, role })
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/admin/matching']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  it('loads stats and the first server page in parallel and exposes no matching mutations', async () => {
    renderApp()
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Matching monitoring' }),
    ).toBeVisible()
    await waitFor(() => {
      expect(readStats).toHaveBeenCalledTimes(1)
      expect(readParticipants).toHaveBeenCalledTimes(1)
    })

    expect(screen.getByText('45')).toBeVisible()
    expect(screen.getByText('31')).toBeVisible()
    expect(screen.getByText('14')).toBeVisible()
    expect(screen.getByText('8')).toBeVisible()
    const table = await screen.findByRole('table', { name: /Matching participant monitoring/ })
    expect(within(table).getByText('Linh Nguyen')).toBeVisible()
    expect(screen.getByText('Showing 1–1 of 45')).toBeVisible()
    expect(screen.getByText('Page 1 of 3')).toBeVisible()
    expect(readParticipants).toHaveBeenCalledWith(
      expect.objectContaining({
        page: 1,
        pageSize: 20,
        studentType: null,
        verified: null,
        zeroBuddiesOnly: false,
      }),
    )
    expect(
      screen.queryByRole('button', { name: /run|preview|publish|override|invite|match/i }),
    ).not.toBeInTheDocument()
  })

  it('delegates backend-supported filters and pagination while resetting the page', async () => {
    renderApp()
    await screen.findByText('Linh Nguyen')
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() =>
      expect(readParticipants).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })),
    )
    fireEvent.change(screen.getByRole('combobox', { name: 'Participation type' }), {
      target: { value: 'INTERNATIONAL' },
    })
    await waitFor(() =>
      expect(readParticipants).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 1, studentType: 'INTERNATIONAL' }),
      ),
    )
    fireEvent.change(screen.getByRole('combobox', { name: 'Email verification' }), {
      target: { value: 'false' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Only participants with zero Buddies' }))
    await waitFor(() =>
      expect(readParticipants).toHaveBeenLastCalledWith(
        expect.objectContaining({
          page: 1,
          studentType: 'INTERNATIONAL',
          verified: false,
          zeroBuddiesOnly: true,
        }),
      ),
    )
    fireEvent.change(screen.getByRole('combobox', { name: 'Rows per page' }), {
      target: { value: '50' },
    })
    await waitFor(() =>
      expect(readParticipants).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 1, pageSize: 50 }),
      ),
    )
  })

  it('opens a localized read-only participant detail with profile preferences', async () => {
    renderApp()
    fireEvent.click(await screen.findByRole('button', { name: 'View details for Linh Nguyen' }))
    expect(
      await screen.findByRole('heading', { name: 'Participant matching profile' }),
    ).toBeVisible()
    expect(readParticipantDetail).toHaveBeenCalledWith(
      expect.objectContaining({ profileId, locale: 'en' }),
    )
    expect(await screen.findByText('Photography')).toBeVisible()
    expect(screen.getByText(/Thai.*Fluent/)).toBeVisible()
    expect(screen.getByText('Formula 1')).toBeVisible()
    expect(screen.queryByText('admin@example.com')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Switch to German/ }))
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Zuordnungsmonitoring' }),
    ).toBeVisible()
    await waitFor(() =>
      expect(readParticipantDetail).toHaveBeenLastCalledWith(
        expect.objectContaining({ profileId, locale: 'de' }),
      ),
    )
  })

  it('shows independent loading, error/retry, and empty states with sanitized copy', async () => {
    const pendingStats = deferred<typeof stats>()
    const pendingParticipants = deferred<AdminMatchingParticipantList>()
    readStats.mockReset().mockReturnValueOnce(pendingStats.promise)
    readParticipants.mockReset().mockReturnValueOnce(pendingParticipants.promise)
    renderApp()
    expect(screen.getByText('Loading matching statistics…')).toBeVisible()
    expect(screen.getByText('Loading data…')).toBeVisible()
    await act(async () => {
      pendingStats.resolve(stats)
      pendingParticipants.resolve(participantPage(1, 20, 0))
    })
    expect(await screen.findByText('No matching participants meet these filters.')).toBeVisible()

    readStats.mockRejectedValueOnce(new Error('database password leaked'))
    readParticipants.mockRejectedValueOnce(new Error('internal SQL leaked'))
    await act(async () => {
      await Promise.all([client.invalidateQueries(), client.refetchQueries()])
    })
    expect(await screen.findByText('Matching statistics could not be loaded.')).toBeVisible()
    expect(screen.getByText('Matching participants could not be loaded.')).toBeVisible()
    expect(screen.queryByText(/password|SQL/i)).not.toBeInTheDocument()

    readStats.mockResolvedValueOnce(stats)
    readParticipants.mockResolvedValueOnce(participantPage())
    const statsRegion = screen.getByRole('region', { name: 'Matching statistics' })
    fireEvent.click(within(statsRegion).getByRole('button', { name: 'Try again' }))
    const tableRegion = screen.getByRole('region', { name: 'Matching participant monitoring' })
    fireEvent.click(within(tableRegion).getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Linh Nguyen')).toBeVisible()
  })

  it('denies USER access before any Admin matching request', async () => {
    renderApp('USER')
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Matching monitoring' })).not.toBeInTheDocument()
    expect(readStats).not.toHaveBeenCalled()
    expect(readParticipants).not.toHaveBeenCalled()
    expect(readParticipantDetail).not.toHaveBeenCalled()
  })

  it('stores monitoring data in private cache and removes it on session cleanup', async () => {
    renderApp()
    await screen.findByText('Linh Nguyen')
    expect(
      client.getQueryCache().findAll({ queryKey: ['private', 'admin-matching'] }),
    ).not.toHaveLength(0)
    await clearPrivateQueries(client)
    expect(
      client.getQueryCache().findAll({ queryKey: ['private', 'admin-matching'] }),
    ).toHaveLength(0)
  })
})
