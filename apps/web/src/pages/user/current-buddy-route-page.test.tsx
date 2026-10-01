import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { CurrentBuddyRoutePage } from '@/pages/user/current-buddy-route-page'
import i18n from '@/i18n'
import { userNavigationItems } from '@/routes/user-navigation'
import { useAuthStore } from '@/stores/auth-store'
import { currentBuddyList } from '@/test/current-buddies'

vi.mock('@/features/chat/chat-conversation', () => ({
  ChatConversation: ({ conversationId, userId }: { conversationId: string; userId: string }) => (
    <div data-testid="chat-page">{`${userId}:${conversationId}`}</div>
  ),
}))

const verifiedUser = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER',
  email_verified: true,
  email_verified_at: '2026-10-01T08:00:00Z',
}

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname + location.search + location.hash}</div>
}

function renderRoute(entry: string) {
  render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/user/buddy" element={<CurrentBuddyRoutePage />} />
        <Route path="/user/matching" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('BUDDY-003 /user/buddy route compatibility', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().setAuthenticated(verifiedUser)
  })
  afterEach(() => useAuthStore.getState().resetSession())

  it('keeps the existing My Buddy navigation surface available', () => {
    expect(userNavigationItems.find(({ id }) => id === 'myBuddy')).toMatchObject({
      available: true,
      to: '/user/buddy',
    })
  })

  it('redirects the existing navigation route to the canonical Current Buddies section', () => {
    renderRoute('/user/buddy')
    expect(screen.getByTestId('location')).toHaveTextContent('/user/matching#current-buddies')
  })

  it('opens the real chat only for the exact approved conversation locator', () => {
    const conversationId = currentBuddyList.items[0].conversation_id
    renderRoute(`/user/buddy?conversation=${conversationId}`)
    expect(screen.getByTestId('chat-page')).toHaveTextContent(
      `${verifiedUser.id}:${conversationId}`,
    )
    expect(screen.queryByTestId('location')).not.toBeInTheDocument()
  })

  it('locks the chat locally after an email identity change removes verification', () => {
    useAuthStore.getState().setAuthenticated({
      ...verifiedUser,
      email: 'replacement@example.com',
      email_verified: false,
      email_verified_at: null,
    })
    renderRoute(`/user/buddy?conversation=${currentBuddyList.items[0].conversation_id}`)
    expect(screen.getByRole('heading', { name: 'Chat is locked' })).toBeVisible()
    expect(screen.queryByTestId('chat-page')).not.toBeInTheDocument()
  })

  it.each([
    '/user/buddy?conversation=not-a-uuid',
    `/user/buddy?conversation=${currentBuddyList.items[0].conversation_id}&next=https://attacker.example`,
    `/user/buddy?conversation=${currentBuddyList.items[0].conversation_id}#private`,
  ])('drops malformed or privilege-bearing route state from %s', (entry) => {
    renderRoute(entry)
    expect(screen.getByTestId('location')).toHaveTextContent('/user/matching#current-buddies')
  })
})
