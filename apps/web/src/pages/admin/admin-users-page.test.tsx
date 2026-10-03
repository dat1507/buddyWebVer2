import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import {
  adminUsersClient,
  type AdminUserList,
  type AdminUserListRequest,
} from '@/features/admin-users/admin-users'
import { clearPrivateQueries } from '@/features/auth/private-cache'
import i18n from '@/i18n'
import { useAuthStore } from '@/stores/auth-store'

const admin = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'admin@example.com',
  role: 'ADMIN' as const,
  email_verified: true,
  email_verified_at: '2026-09-20T08:30:00Z',
}
const student = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'ada@example.com',
  role: 'USER' as const,
  is_active: true,
  email_verified: true,
  created_at: '2026-09-20T08:30:00Z',
  profile: {
    id: '22222222-2222-4222-8222-222222222222',
    full_name: 'Ada Student',
    display_name: 'Ada',
    student_type: 'INTERNATIONAL' as const,
  },
}

function userPage(page = 1, pageSize = 20, total = 45): AdminUserList {
  return {
    items: total ? [student] : [],
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

describe('ADMIN-012 guarded Admin User Management page', () => {
  let client: QueryClient
  const readUsers = vi.spyOn(adminUsersClient, 'readUsers')

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    readUsers.mockReset().mockImplementation(async ({ page, pageSize }) => userPage(page, pageSize))
  })

  afterEach(() => {
    client.clear()
    useAuthStore.getState().resetSession()
    vi.clearAllMocks()
  })

  const renderApp = (role: 'ADMIN' | 'USER' | null = 'ADMIN') => {
    if (role) useAuthStore.getState().setAuthenticated({ ...admin, role })
    else useAuthStore.getState().clearSession()
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/admin/users']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  it('loads a direct route into the real table and renders only explicit summary fields', async () => {
    renderApp()
    expect(await screen.findByRole('heading', { level: 1, name: 'User management' })).toBeVisible()
    const table = await screen.findByRole('table', { name: 'Student accounts' })
    expect(within(table).getByText('Ada')).toBeVisible()
    expect(within(table).getByText('Ada Student')).toBeVisible()
    expect(within(table).getByText('ada@example.com')).toBeVisible()
    expect(within(table).getByText('International student')).toBeVisible()
    expect(within(table).getByText('Verified')).toBeVisible()
    expect(within(table).getByText('Active')).toBeVisible()
    expect(screen.getByText('Showing 1–1 of 45')).toBeVisible()
    expect(screen.getByText('Page 1 of 3')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Users' })).toHaveAttribute('aria-current', 'page')
    expect(readUsers).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, pageSize: 20, search: '' }),
    )
    expect(screen.queryByText(/password|last.login|object.key/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /details/i })).not.toBeInTheDocument()
  })

  it('debounces backend search and resets pagination before requesting filtered results', async () => {
    renderApp()
    await screen.findByText('ada@example.com')
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() =>
      expect(readUsers).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2, search: '' })),
    )

    fireEvent.change(screen.getByRole('searchbox', { name: 'Search users' }), {
      target: { value: '  Ada  ' },
    })
    expect(screen.getByText('Loading data…')).toBeVisible()
    await waitFor(
      () =>
        expect(readUsers).toHaveBeenLastCalledWith(
          expect.objectContaining({ page: 1, pageSize: 20, search: 'Ada' }),
        ),
      { timeout: 1_500 },
    )
  })

  it('delegates page-size changes and recovers deterministically from an empty out-of-range page', async () => {
    readUsers.mockImplementation(async ({ page, pageSize }: AdminUserListRequest) => {
      if (page === 2) return { items: [], page: 2, page_size: pageSize, total: 5, total_pages: 1 }
      return userPage(page, pageSize, pageSize === 50 ? 75 : 25)
    })
    renderApp()
    await screen.findByText('ada@example.com')
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() =>
      expect(readUsers).toHaveBeenCalledWith(expect.objectContaining({ page: 2, pageSize: 20 })),
    )
    await waitFor(() => expect(readUsers).toHaveBeenCalledTimes(3))
    expect(readUsers).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, pageSize: 20 }))
    expect(await screen.findByText('Page 1 of 2')).toBeVisible()

    fireEvent.change(screen.getByRole('combobox', { name: 'Rows per page' }), {
      target: { value: '50' },
    })
    await waitFor(() =>
      expect(readUsers).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 1, pageSize: 50 }),
      ),
    )
    expect(await screen.findByText('Page 1 of 2')).toBeVisible()
  })

  it('shows accessible loading, empty, and no-search-result states', async () => {
    const pending = deferred<AdminUserList>()
    readUsers.mockReset().mockReturnValueOnce(pending.promise)
    renderApp()
    expect(screen.getByText('Loading data…')).toHaveAttribute('role', 'status')
    expect(screen.getByRole('table', { name: 'Student accounts' })).toHaveAttribute(
      'aria-busy',
      'true',
    )
    await act(async () => pending.resolve(userPage(1, 20, 0)))
    expect(await screen.findByText('There are no student accounts to show.')).toBeVisible()

    readUsers.mockResolvedValueOnce(userPage(1, 20, 0))
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search users' }), {
      target: { value: 'Nobody' },
    })
    expect(await screen.findByText('No student accounts match this search.')).toBeVisible()
  })

  it('shows only a safe error and retries successfully', async () => {
    readUsers.mockReset().mockRejectedValueOnce(new Error('database password leaked'))
    renderApp()
    expect(await screen.findByRole('alert')).toHaveTextContent('The user list could not be loaded.')
    expect(screen.queryByText(/database password/i)).not.toBeInTheDocument()

    readUsers.mockResolvedValueOnce(userPage())
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('ada@example.com')).toBeVisible()
  })

  it.each([['USER', /Connect with/] as const, [null, 'Administration access'] as const])(
    'denies %s before making an Admin users request',
    async (role, publicHeading) => {
      renderApp(role)
      expect(await screen.findByRole('heading', { name: publicHeading })).toBeVisible()
      expect(screen.queryByRole('heading', { name: 'User management' })).not.toBeInTheDocument()
      expect(readUsers).not.toHaveBeenCalled()
    },
  )

  it('uses the private cache and removes data before a wrong-role view can render it', async () => {
    renderApp()
    await screen.findByText('ada@example.com')
    expect(
      client.getQueryCache().findAll({ queryKey: ['private', 'admin-users'] }),
    ).not.toHaveLength(0)
    await act(async () => clearPrivateQueries(client))
    expect(client.getQueryCache().findAll({ queryKey: ['private', 'admin-users'] })).toHaveLength(0)

    act(() => useAuthStore.getState().setAuthenticated({ ...admin, role: 'USER' }))
    expect(screen.queryByText('ada@example.com')).not.toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
  })

  it('switches all page controls and table labels to German without another request', async () => {
    renderApp()
    await screen.findByText('ada@example.com')
    fireEvent.click(screen.getByRole('button', { name: /Switch to German/ }))
    const heading = await screen.findByRole('heading', { name: 'Benutzerverwaltung' })
    expect(heading).toBeVisible()
    expect(heading).toHaveClass('break-words', 'text-3xl', 'sm:text-4xl')
    expect(screen.getByRole('searchbox', { name: 'Benutzer suchen' })).toHaveAttribute(
      'placeholder',
      'E-Mail, vollständiger Name oder Anzeigename',
    )
    expect(screen.getByRole('table', { name: 'Studierendenkonten' })).toBeVisible()
    expect(screen.getByText('Internationale Studierende')).toBeVisible()
    expect(readUsers).toHaveBeenCalledTimes(1)
  })

  it('keeps the wide table inside a keyboard-focusable horizontal scroll region', async () => {
    renderApp()
    await screen.findByText('ada@example.com')
    const region = screen.getByRole('region', { name: 'Scrollable table: Student accounts' })
    expect(region).toHaveAttribute('tabindex', '0')
    expect(region).toHaveClass('overflow-x-auto', 'max-w-full')
    expect(screen.getByRole('navigation', { name: 'Pagination: Student accounts' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
  })
})
