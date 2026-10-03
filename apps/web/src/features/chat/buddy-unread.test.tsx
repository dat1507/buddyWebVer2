import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { Navbar } from '@/components/layout/navbar'
import { UserSidebarNavigation } from '@/components/layout/user-sidebar-navigation'
import { BuddyUnreadProvider } from '@/features/chat/buddy-unread'
import { chatClient } from '@/features/chat/chat-client'
import { CurrentBuddiesSection } from '@/features/matching/current-buddies-section'
import { matchingClient } from '@/features/matching/matching-client'
import { useCurrentBuddies } from '@/features/matching/queries/use-current-buddies'
import i18n from '@/i18n'
import { useAuthStore } from '@/stores/auth-store'
import { currentBuddyList } from '@/test/current-buddies'

const conversationId = 'bbbbbbbb-1111-4111-8111-111111111111'

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  readonly url: string
  private readonly listeners = new Map<
    string,
    Set<(event: { data?: string; code?: number }) => void>
  >()

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  addEventListener(type: string, listener: (event: { data?: string; code?: number }) => void) {
    const listeners = this.listeners.get(type) ?? new Set()
    listeners.add(listener)
    this.listeners.set(type, listeners)
  }

  close() {}

  emitMessage(payload: unknown) {
    this.listeners
      .get('message')
      ?.forEach((listener) => listener({ data: JSON.stringify(payload) }))
  }

  emitClose(code = 1006) {
    this.listeners.get('close')?.forEach((listener) => listener({ code }))
  }
}

const unread = (count: number) => ({
  total_unread_messages: count,
  conversations: count > 0 ? [{ conversation_id: conversationId, unread_count: count }] : [],
})

const multipleUnread = {
  total_unread_messages: 2,
  conversations: [
    { conversation_id: conversationId, unread_count: 1 },
    { conversation_id: 'bbbbbbbb-2222-4222-8222-222222222222', unread_count: 1 },
  ],
}

function BuddyListFixture() {
  const query = useCurrentBuddies({ enabled: true, locale: 'en' })
  return <CurrentBuddiesSection enabled locale="en" query={query} targetConversationId={null} />
}

describe('authoritative Buddy unread indicators', () => {
  let client: QueryClient

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    useAuthStore.getState().setAuthenticated({
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      email: 'student@example.com',
      role: 'USER',
      email_verified: true,
      email_verified_at: '2026-10-01T08:00:00Z',
    })
    FakeWebSocket.instances = []
    vi.stubGlobal('WebSocket', FakeWebSocket)
    vi.stubEnv('VITE_API_URL', 'https://api.example.test/api')
  })

  afterEach(() => {
    client.clear()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  const renderIndicators = () =>
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <BuddyUnreadProvider>
            <Navbar />
            <UserSidebarNavigation />
          </BuddyUnreadProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )

  it('shows the same persisted count on My Buddy and Open workspace after a fresh mount', async () => {
    vi.spyOn(chatClient, 'readUnreadSummary').mockResolvedValue(unread(2))
    renderIndicators()

    expect(await screen.findAllByLabelText('2 unread Buddy messages')).toHaveLength(2)
    expect(screen.getByRole('link', { name: /My Buddy.*2 unread Buddy messages/ })).toBeVisible()
    expect(
      screen.getByRole('link', { name: /Open workspace.*2 unread Buddy messages/ }),
    ).toBeVisible()
    expect(FakeWebSocket.instances[0].url).toBe('wss://api.example.test/api/ws/chat/notifications')
  })

  it('reconciles from the backend on realtime, duplicate, and reconnect events', async () => {
    const service = vi
      .spyOn(chatClient, 'readUnreadSummary')
      .mockResolvedValueOnce(unread(1))
      .mockResolvedValue(unread(3))
    renderIndicators()
    expect(await screen.findAllByLabelText('1 unread Buddy message')).toHaveLength(2)

    await act(async () => {
      FakeWebSocket.instances[0].emitMessage({
        type: 'chat.unread.changed',
        recovery: 'unread-summary',
      })
      FakeWebSocket.instances[0].emitMessage({
        type: 'chat.unread.changed',
        recovery: 'unread-summary',
      })
    })
    expect(await screen.findAllByLabelText('3 unread Buddy messages')).toHaveLength(2)
    expect(screen.queryByLabelText('6 unread Buddy messages')).not.toBeInTheDocument()

    service.mockResolvedValue(unread(0))
    act(() => FakeWebSocket.instances[0].emitClose())
    await waitFor(() => {
      expect(screen.queryByLabelText(/unread Buddy message/)).not.toBeInTheDocument()
    })
  })

  it('shows the persisted per-conversation count on the matching Buddy card', async () => {
    vi.spyOn(chatClient, 'readUnreadSummary').mockResolvedValue(unread(2))
    vi.spyOn(matchingClient, 'readCurrentBuddies').mockResolvedValue(currentBuddyList)
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <BuddyUnreadProvider>
            <BuddyListFixture />
          </BuddyUnreadProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByLabelText('2 unread Buddy messages')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Start chatting with Linh' })).toHaveAttribute(
      'href',
      `/user/buddy?conversation=${conversationId}`,
    )
  })

  it('keeps the global indicator while another conversation remains unread', async () => {
    const service = vi
      .spyOn(chatClient, 'readUnreadSummary')
      .mockResolvedValueOnce(multipleUnread)
      .mockResolvedValue({
        total_unread_messages: 1,
        conversations: [multipleUnread.conversations[1]],
      })
    renderIndicators()
    expect(await screen.findAllByLabelText('2 unread Buddy messages')).toHaveLength(2)

    await act(async () => {
      FakeWebSocket.instances[0].emitMessage({
        type: 'chat.unread.changed',
        recovery: 'unread-summary',
      })
    })

    expect(await screen.findAllByLabelText('1 unread Buddy message')).toHaveLength(2)
    expect(service).toHaveBeenCalledTimes(2)
  })
})
