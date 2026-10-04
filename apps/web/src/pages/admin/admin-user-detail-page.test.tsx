import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import {
  adminMatchingClient,
  type AdminMatchingParticipantDetail,
} from '@/features/admin-matching/admin-matching'
import {
  adminUsersClient,
  type AdminUserDetail,
  type AdminUserList,
} from '@/features/admin-users/admin-users'
import { clearPrivateQueries } from '@/features/auth/private-cache'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/auth-store'

const userId = '11111111-1111-4111-8111-111111111111'
const profileId = '22222222-2222-4222-8222-222222222222'
const admin = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'admin@example.com',
  role: 'ADMIN' as const,
  email_verified: true,
  email_verified_at: '2026-09-20T08:30:00Z',
}
const detail: AdminUserDetail = {
  id: userId,
  email: 'ada@example.com',
  role: 'USER',
  is_active: true,
  email_verified: true,
  created_at: '2026-09-20T08:30:00Z',
  profile: {
    id: profileId,
    full_name: 'Ada Student',
    display_name: 'Ada',
    student_type: 'INTERNATIONAL',
    nationality: 'British',
    major: 'Computer Science',
    study_year: 2,
    bio: 'Exchange student',
    home_university: 'Example University',
    arrival_date: '2026-09-01',
    departure_date: '2027-02-28',
    matching_opt_in: true,
    onboarding_completed_at: '2026-09-21T10:00:00Z',
    avatar: null,
  },
}
const matchingDetail: AdminMatchingParticipantDetail = {
  profile: {
    id: profileId,
    display_name: 'Ada',
    student_type: 'INTERNATIONAL',
    major: 'Computer Science',
    avatar: null,
    interests: [
      {
        id: '33333333-3333-4333-8333-333333333333',
        code: 'private-interest',
        label: 'Private interest label',
        is_custom: false,
      },
    ],
    languages: [
      { code: 'en', label: 'Private language label', proficiency: 'native', is_custom: false },
    ],
    activities: [
      {
        id: '44444444-4444-4444-8444-444444444444',
        code: 'board-games',
        label: 'Board games',
        is_custom: false,
      },
    ],
    availability: null,
  },
  is_active: true,
  email_verified: true,
  matching_opt_in: true,
  buddy_count: 1,
}
const list: AdminUserList = {
  items: [
    {
      id: detail.id,
      email: detail.email,
      role: detail.role,
      is_active: detail.is_active,
      email_verified: detail.email_verified,
      created_at: detail.created_at,
      profile: detail.profile
        ? {
            id: detail.profile.id,
            full_name: detail.profile.full_name,
            display_name: detail.profile.display_name,
            student_type: detail.profile.student_type,
          }
        : null,
    },
  ],
  page: 1,
  page_size: 20,
  total: 1,
  total_pages: 1,
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

describe('ADMIN-013 guarded Admin user detail page', () => {
  let client: QueryClient
  const readUsers = vi.spyOn(adminUsersClient, 'readUsers')
  const readUserDetail = vi.spyOn(adminUsersClient, 'readUserDetail')
  const readMatchingDetail = vi.spyOn(adminMatchingClient, 'readParticipantDetail')

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    readUsers.mockReset().mockResolvedValue(list)
    readUserDetail.mockReset().mockResolvedValue(detail)
    readMatchingDetail.mockReset().mockResolvedValue(matchingDetail)
  })

  afterEach(() => {
    client.clear()
    useAuthStore.getState().resetSession()
    vi.clearAllMocks()
  })

  function renderApp(path = `/admin/users/${userId}`, role: 'ADMIN' | 'USER' | null = 'ADMIN') {
    if (role) useAuthStore.getState().setAuthenticated({ ...admin, role })
    else useAuthStore.getState().clearSession()
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  it('navigates list to detail and back while keeping Users selected', async () => {
    renderApp('/admin/users')
    fireEvent.click(await screen.findByRole('link', { name: 'View details for Ada' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Ada' })).toBeVisible()
    expect(readUserDetail).toHaveBeenCalledWith(expect.objectContaining({ userId }))
    expect(readMatchingDetail).toHaveBeenCalledWith(
      expect.objectContaining({ profileId, locale: 'en' }),
    )
    expect(screen.getByRole('link', { name: 'Users' })).toHaveAttribute('aria-current', 'page')

    fireEvent.click(screen.getByRole('link', { name: 'Back to users' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'User management' })).toBeVisible()
  })

  it('renders only allowlisted account, profile, authoritative matching, and narrow activity data', async () => {
    renderApp()

    expect(await screen.findByRole('heading', { name: 'Account summary' })).toBeVisible()
    expect(screen.getByRole('heading', { level: 1, name: 'Ada' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Profile information' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Buddy status' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Activity and milestones' })).toBeVisible()
    expect(screen.getAllByText('ada@example.com')).toHaveLength(2)
    expect(screen.getByText('British')).toBeVisible()
    expect(screen.getByText('Example University')).toBeVisible()
    expect(screen.getByText('Active Buddy relationship')).toBeVisible()
    expect(screen.getByText('Board games')).toBeVisible()
    expect(screen.queryByText('Private interest label')).not.toBeInTheDocument()
    expect(screen.queryByText('Private language label')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /edit|save|delete|deactivate/i }),
    ).not.toBeInTheDocument()
  })

  it('announces loading and resolves a direct-route refresh', async () => {
    const pending = deferred<AdminUserDetail>()
    readUserDetail.mockReset().mockReturnValueOnce(pending.promise)
    renderApp()

    expect(screen.getByRole('status')).toHaveTextContent('Loading user details…')
    await act(async () => pending.resolve(detail))
    expect(await screen.findByRole('heading', { level: 1, name: 'Ada' })).toBeVisible()
    expect(readMatchingDetail).toHaveBeenCalledTimes(1)
  })

  it('shows safe not-found states and does not request an invalid id', async () => {
    readUserDetail.mockRejectedValueOnce(new ApiError(404, 'notFound'))
    const view = renderApp()
    expect(await screen.findByRole('heading', { name: 'User not found' })).toBeVisible()
    expect(readMatchingDetail).not.toHaveBeenCalled()

    view.unmount()
    client.clear()
    readUserDetail.mockClear()
    renderApp('/admin/users/not-a-uuid')
    expect(await screen.findByRole('heading', { name: 'User not found' })).toBeVisible()
    expect(readUserDetail).not.toHaveBeenCalled()
  })

  it('shows a safe generic error and retries successfully', async () => {
    readUserDetail.mockRejectedValueOnce(new Error('database password leaked'))
    renderApp()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The user details could not be loaded.',
    )
    expect(screen.queryByText(/database password/i)).not.toBeInTheDocument()
    readUserDetail.mockResolvedValueOnce(detail)
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Ada' })).toBeVisible()
  })

  it.each([['USER', /Connect with/] as const, [null, 'Administration access'] as const])(
    'denies %s before requesting Admin detail APIs',
    async (role, publicHeading) => {
      renderApp(`/admin/users/${userId}`, role)
      expect(await screen.findByRole('heading', { name: publicHeading })).toBeVisible()
      expect(readUserDetail).not.toHaveBeenCalled()
      expect(readMatchingDetail).not.toHaveBeenCalled()
    },
  )

  it('stores both detail queries privately and clears them before a role switch', async () => {
    renderApp()
    await screen.findByRole('heading', { level: 1, name: 'Ada' })
    expect(client.getQueryCache().findAll({ queryKey: ['private', 'admin-users'] })).toHaveLength(1)
    expect(
      client.getQueryCache().findAll({ queryKey: ['private', 'admin-matching'] }),
    ).not.toHaveLength(0)

    act(() => useAuthStore.getState().setAuthenticated({ ...admin, role: 'USER' }))
    expect(screen.queryByText('ada@example.com')).not.toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()

    await act(async () => clearPrivateQueries(client))
    expect(client.getQueryCache().findAll({ queryKey: ['private', 'admin-users'] })).toHaveLength(0)
    expect(
      client.getQueryCache().findAll({ queryKey: ['private', 'admin-matching'] }),
    ).toHaveLength(0)
  })

  it('switches to German, refetches localized activity labels, and keeps responsive wrapping', async () => {
    renderApp()
    await screen.findByRole('heading', { level: 1, name: 'Ada' })
    fireEvent.click(screen.getByRole('button', { name: /Switch to German/ }))

    const heading = await screen.findByRole('heading', { level: 1, name: 'Ada' })
    expect(screen.getByRole('heading', { name: 'Kontozusammenfassung' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Zurück zur Benutzerliste' })).toBeVisible()
    await waitFor(() =>
      expect(readMatchingDetail).toHaveBeenLastCalledWith(
        expect.objectContaining({ profileId, locale: 'de' }),
      ),
    )
    expect(screen.getByTestId('admin-user-detail')).toHaveClass('min-w-0')
    expect(heading).toHaveClass('break-words', 'text-3xl', 'sm:text-4xl')
    expect(screen.getAllByText('ada@example.com')).toHaveLength(2)
    expect(
      screen.getAllByText('ada@example.com').every((node) => node.classList.contains('break-all')),
    ).toBe(true)
  })
})
