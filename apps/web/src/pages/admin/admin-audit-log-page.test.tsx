import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import App from '@/App'
import { adminAuditClient, type AuditActivity } from '@/features/admin-audit-log'
import { clearPrivateQueries } from '@/features/auth/private-cache'
import i18n from '@/i18n'
import { useAuthStore } from '@/stores/auth-store'

const actor = { id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', email: 'admin-a@example.com' }
const second = { id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', email: 'admin-b@example.com' }
const entry: AuditActivity = {
  id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  admin_id: actor.id,
  admin_email: actor.email,
  created_at: '2026-11-07T07:35:00Z',
  action: 'event.status_update.PUBLISHED',
  category: 'events',
  resource_type: 'event',
  resource_id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
  before_status: null,
  after_status: 'PUBLISHED',
}
const items = [
  entry,
  {
    ...entry,
    id: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
    admin_id: second.id,
    admin_email: second.email,
    action: 'unknown',
    after_status: null,
  },
]
const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
const list = vi.spyOn(adminAuditClient, 'list')
const actors = vi.spyOn(adminAuditClient, 'actors')

function openAuditLog() {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/admin/audit-log']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(async () => {
  await i18n.changeLanguage('en')
  useAuthStore.getState().setAuthenticated({ ...actor, role: 'ADMIN', email_verified: true })
  actors.mockResolvedValue({ items: [actor, second], has_more: false })
  list.mockImplementation(async (params) => ({
    items,
    page: Number(params.get('page')),
    page_size: 20,
    total: 21,
    total_pages: 2,
  }))
})

afterEach(() => {
  cleanup()
  client.clear()
  list.mockReset()
  actors.mockReset()
  useAuthStore.getState().resetSession()
})

it('attributes rows independently and opens safe localized details with keyboard focus restoration', async () => {
  // JSDOM does not implement the native modal API. Browser acceptance covers the top layer.
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: {
      configurable: true,
      value(this: HTMLDialogElement) {
        this.open = true
      },
    },
    close: {
      configurable: true,
      value(this: HTMLDialogElement) {
        this.open = false
      },
    },
  })
  openAuditLog()
  const navigation = screen.getByRole('navigation', { name: 'Administrator navigation' })
  expect(within(navigation).getByRole('link', { name: 'Audit Log' })).toHaveAttribute(
    'aria-current',
    'page',
  )
  const published = await screen.findByRole('row', { name: /Published an event/ })
  expect(published).toHaveTextContent(actor.email)
  expect(published).toHaveTextContent('2:35:00 PM (GMT+7)')
  expect(screen.getByRole('row', { name: /Administrative activity/ })).toHaveTextContent(
    second.email,
  )
  const opener = within(published).getByRole('button', { name: /View details/ })
  opener.focus()
  fireEvent.click(opener)
  const modal = screen.getByRole('dialog', { name: 'Activity details' })
  expect(modal).toHaveTextContent('Published an event')
  expect(modal).toHaveTextContent(entry.resource_id!)
  expect(within(modal).getByRole('button', { name: 'Close' })).toHaveFocus()
  fireEvent(modal, new Event('cancel', { bubbles: false, cancelable: true }))
  expect(modal).not.toBeInTheDocument()
  expect(opener).toHaveFocus()

  fireEvent.click(screen.getByRole('button', { name: /Switch to German/ }))
  expect(await screen.findByRole('heading', { name: 'Aktivitätsprotokoll' })).toBeVisible()
  expect(screen.getByRole('row', { name: /Veranstaltung veröffentlicht/ })).toHaveTextContent(
    '14:35:00 (GMT+7)',
  )
  expect(list).toHaveBeenCalledTimes(1)
})

it('applies server filters and resets pagination, including custom calendar dates', async () => {
  openAuditLog()
  await screen.findByRole('row', { name: /Published an event/ })
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  await waitFor(() => expect(list.mock.lastCall?.[0].get('page')).toBe('2'))
  fireEvent.change(screen.getByRole('combobox', { name: 'Admin' }), {
    target: { value: second.id },
  })
  await waitFor(() =>
    expect(list.mock.lastCall?.[0].toString()).toBe('page=1&period=month&admin_id=' + second.id),
  )
  fireEvent.change(screen.getByRole('combobox', { name: 'Activity category' }), {
    target: { value: 'events' },
  })
  await waitFor(() => expect(list.mock.lastCall?.[0].get('category')).toBe('events'))
  fireEvent.change(screen.getByRole('combobox', { name: 'Time period' }), {
    target: { value: 'custom' },
  })
  expect(screen.getByText('Choose a date range of up to 366 days.')).toBeVisible()
  fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-11-06' } })
  fireEvent.change(screen.getByLabelText('Through'), { target: { value: '2026-11-07' } })
  await waitFor(() => expect(list.mock.lastCall?.[0].get('end')).toBe('2026-11-07'))
  expect(list.mock.lastCall?.[0].get('start')).toBe('2026-11-06')
})

it('shows loading, retry and empty states and clears actor and activity data with private cache cleanup', async () => {
  let reject!: (reason: Error) => void
  list.mockImplementationOnce(
    () =>
      new Promise((_resolve, fail) => {
        reject = fail
      }),
  )
  openAuditLog()
  expect(await screen.findByText('Loading data…')).toBeVisible()
  reject(new Error('synthetic failure'))
  expect(await screen.findByText('The activity history could not be loaded.')).toBeVisible()
  list.mockResolvedValue({ items: [], page: 1, page_size: 20, total: 0, total_pages: 0 })
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('No activity matches these filters.')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
  await waitFor(() => expect(list).toHaveBeenCalledTimes(3))
  cleanup()
  expect(client.getQueryCache().findAll({ queryKey: ['private', actor.id] })).toHaveLength(2)
  await clearPrivateQueries(client)
  expect(client.getQueryCache().findAll({ queryKey: ['private', actor.id] })).toHaveLength(0)
})
