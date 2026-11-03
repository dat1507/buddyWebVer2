import { act, fireEvent, render, screen } from '@testing-library/react'
import { Link, MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ChatbotEntry } from './chatbot-entry'
import { ChatbotBoundary } from './chatbot-boundary'
import i18n from '@/i18n'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'synthetic@example.invalid',
  role: 'USER',
  email_verified: true,
  email_verified_at: '2026-10-22T00:00:00Z',
}
function view(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Link to="/merchandise">Next page</Link>
      <ChatbotEntry />
    </MemoryRouter>,
  )
}

describe('chatbot route and deployment exposure boundary', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().clearSession()
  })
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllEnvs()
    useAuthStore.getState().clearSession()
  })
  it('contains optional-widget failures without breaking the surrounding page', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    function Broken(): never {
      throw new Error('opaque chunk failure')
    }
    render(
      <>
        <p>Surrounding page</p>
        <ChatbotBoundary>
          <Broken />
        </ChatbotBoundary>
      </>,
    )
    expect(screen.getByText('Surrounding page')).toBeVisible()
    expect(screen.getByRole('status')).toHaveTextContent('temporarily unavailable')
    expect(screen.queryByText('opaque chunk failure')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Close assistant' }))
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
  it.each([undefined, 'false', 'TRUE', '1'])('defaults OFF for %s', (flag) => {
    vi.stubEnv('VITE_CHATBOT_ENABLED', flag)
    view()
    expect(screen.queryByRole('button', { name: /Assistant/ })).not.toBeInTheDocument()
  })
  it.each(['/', '/merchandise', '/events/recap', '/login', '/register', '/verify-email'])(
    'supports public route %s',
    async (path) => {
      vi.stubEnv('VITE_CHATBOT_ENABLED', 'true')
      view(path)
      expect(await screen.findByRole('button', { name: 'Open VGU Buddy Assistant' })).toBeVisible()
    },
  )
  it.each(['/admin', '/admin/dashboard', '/adminLogin', '/unknown'])('excludes %s', (path) => {
    vi.stubEnv('VITE_CHATBOT_ENABLED', 'true')
    view(path)
    expect(screen.queryByRole('button', { name: /Assistant/ })).not.toBeInTheDocument()
  })
  it('supports authenticated User routes but hides Admin sessions', async () => {
    vi.stubEnv('VITE_CHATBOT_ENABLED', 'true')
    useAuthStore.getState().setAuthenticated(user)
    view('/user/dashboard')
    expect(await screen.findByRole('button', { name: 'Open VGU Buddy Assistant' })).toBeVisible()
    act(() =>
      useAuthStore.getState().setAuthenticated({ ...user, role: 'ADMIN', email_verified_at: null }),
    )
    expect(screen.queryByRole('button', { name: /Assistant/ })).not.toBeInTheDocument()
  })
  it('keeps the widget open across supported route transitions', async () => {
    vi.stubEnv('VITE_CHATBOT_ENABLED', 'true')
    view()
    fireEvent.click(await screen.findByRole('button', { name: 'Open VGU Buddy Assistant' }))
    await screen.findByRole('textbox')
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'In-memory draft' } })
    fireEvent.click(screen.getByRole('link', { name: 'Next page' }))
    expect(screen.getByRole('textbox')).toHaveValue('In-memory draft')
  })
  it('resets the mounted conversation on identity change', async () => {
    vi.stubEnv('VITE_CHATBOT_ENABLED', 'true')
    view()
    fireEvent.click(await screen.findByRole('button', { name: 'Open VGU Buddy Assistant' }))
    await screen.findByRole('textbox')
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Private fixture draft' } })
    act(() => useAuthStore.getState().setAuthenticated(user))
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: 'Open VGU Buddy Assistant' }))
    expect(await screen.findByRole('textbox')).toHaveValue('')
  })
})
