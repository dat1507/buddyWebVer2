import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { chatClient } from '@/features/chat/chat-client'
import { buddyUnreadQueryKeys } from '@/features/chat/buddy-unread-state'
import { ChatConversation } from '@/features/chat/chat-conversation'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'

const conversationId = '30000000-0000-4000-8000-000000000001'
const secondConversationId = '30000000-0000-4000-8000-000000000002'
const userId = '30000000-0000-4000-8000-000000000003'
const clientMessageId = '30000000-0000-4000-8000-000000000004'

const message = (id: string, sender: 'self' | 'buddy', body: string, createdAt: string) => ({
  id,
  sender,
  body,
  created_at: createdAt,
  read_at: null,
})

class FakeWebSocket extends EventTarget {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSING = 2
  static readonly CLOSED = 3
  static instances: FakeWebSocket[] = []

  readonly url: string
  readyState = FakeWebSocket.CONNECTING
  sent: string[] = []

  constructor(url: string | URL) {
    super()
    this.url = String(url)
    FakeWebSocket.instances.push(this)
  }

  send(data: string | ArrayBufferLike | Blob | ArrayBufferView) {
    if (typeof data === 'string') this.sent.push(data)
  }

  close(code = 1000, reason = '') {
    if (this.readyState === FakeWebSocket.CLOSED) return
    this.readyState = FakeWebSocket.CLOSED
    this.dispatchEvent(new CloseEvent('close', { code, reason }))
  }

  serverEvent(payload: unknown) {
    this.dispatchEvent(new MessageEvent('message', { data: JSON.stringify(payload) }))
  }

  ready() {
    this.readyState = FakeWebSocket.OPEN
    this.serverEvent({ type: 'chat.ready', recovery: 'history' })
  }
}

describe('CHAT-004 accessible conversation UI', () => {
  let client: QueryClient

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    vi.stubEnv('VITE_API_URL', 'https://api.example.test/api')
    vi.stubGlobal('WebSocket', FakeWebSocket)
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      callback(0)
      return 1
    })
    vi.stubGlobal('crypto', { ...crypto, randomUUID: vi.fn(() => clientMessageId) })
    FakeWebSocket.instances = []
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    vi.spyOn(chatClient, 'acknowledgeMessages').mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.useRealTimers()
    client.clear()
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  const renderChat = (targetConversationId = conversationId) =>
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <ChatConversation
            key={`${userId}:${targetConversationId}`}
            conversationId={targetConversationId}
            userId={userId}
          />
        </MemoryRouter>
      </QueryClientProvider>,
    )

  it('renders chronological bounded history, safely prepends older messages and acknowledges the latest incoming boundary', async () => {
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const older = message(
      '30000000-0000-4000-8000-000000000010',
      'buddy',
      'Oldest',
      '2026-10-01T08:00:00Z',
    )
    const incoming = message(
      '30000000-0000-4000-8000-000000000011',
      'buddy',
      '<img src=x onerror=alert(1)>',
      '2026-10-01T08:01:00Z',
    )
    const own = message(
      '30000000-0000-4000-8000-000000000012',
      'self',
      'Newest',
      '2026-10-01T08:02:00Z',
    )
    vi.spyOn(chatClient, 'readMessages').mockImplementation(async ({ before }) =>
      before
        ? { items: [older], next_before: null, page_size: 50 }
        : { items: [incoming, own], next_before: 'opaque-cursor', page_size: 50 },
    )

    renderChat()

    expect(await screen.findByRole('heading', { name: 'Buddy chat' })).toBeVisible()
    const log = screen.getByRole('log', { name: 'Conversation messages' })
    expect(within(log).getByText('<img src=x onerror=alert(1)>')).toBeVisible()
    expect(log.querySelector('img')).toBeNull()
    expect(Array.from(log.querySelectorAll('li')).map((item) => item.textContent)).toEqual([
      expect.stringContaining('<img src=x onerror=alert(1)>'),
      expect.stringContaining('Newest'),
    ])
    await waitFor(() =>
      expect(chatClient.acknowledgeMessages).toHaveBeenCalledWith({
        conversationId,
        throughMessageId: incoming.id,
      }),
    )
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: buddyUnreadQueryKeys.summary(userId),
      exact: true,
    })

    fireEvent.click(screen.getByRole('button', { name: 'Load older messages' }))
    expect(await within(log).findByText('Oldest')).toBeVisible()
    expect(Array.from(log.querySelectorAll('li')).map((item) => item.textContent)).toEqual([
      expect.stringContaining('Oldest'),
      expect.stringContaining('<img src=x onerror=alert(1)>'),
      expect.stringContaining('Newest'),
    ])
    expect(chatClient.readMessages).toHaveBeenCalledWith(
      expect.objectContaining({ before: 'opaque-cursor' }),
    )
  })

  it('sends once over WebSocket, reconciles the authoritative echo and deduplicates repeats', async () => {
    vi.spyOn(chatClient, 'readMessages').mockResolvedValue({
      items: [],
      next_before: null,
      page_size: 50,
    })
    const sendHttp = vi.spyOn(chatClient, 'sendMessage')
    renderChat()
    await screen.findByRole('heading', { name: 'Buddy chat' })
    const socket = FakeWebSocket.instances[0]
    act(() => socket.ready())
    expect(await screen.findByText('Live updates connected')).toBeVisible()

    fireEvent.change(screen.getByRole('textbox', { name: 'Message' }), {
      target: { value: 'Hello\nBuddy' },
    })
    const send = screen.getByRole('button', { name: 'Send message' })
    fireEvent.click(send)
    fireEvent.click(send)

    expect(socket.sent).toHaveLength(1)
    expect(JSON.parse(socket.sent[0])).toEqual({
      type: 'message.send',
      client_message_id: clientMessageId,
      body: 'Hello\nBuddy',
    })
    expect(sendHttp).not.toHaveBeenCalled()
    expect(screen.getAllByText('Sending…')).toHaveLength(2)

    const persisted = message(
      '30000000-0000-4000-8000-000000000020',
      'self',
      'Hello\nBuddy',
      '2026-10-01T08:03:00Z',
    )
    act(() => {
      socket.serverEvent({
        type: 'chat.message.accepted',
        message_id: persisted.id,
        realtime_delivery: 'published',
        recovery: 'history',
      })
    })

    expect(await screen.findByText('Sent. Synchronizing with history…')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Send message' })).toBeDisabled()

    act(() => {
      socket.serverEvent({ type: 'chat.message.created', message: persisted })
      socket.serverEvent({ type: 'chat.message.created', message: persisted })
    })

    await waitFor(() => expect(screen.queryAllByText('Sending…')).toHaveLength(0))
    expect(screen.queryByText('Sent. Synchronizing with history…')).not.toBeInTheDocument()
    expect(screen.getAllByText(/Hello/)).toHaveLength(1)
    expect(chatClient.acknowledgeMessages).not.toHaveBeenCalled()
  })

  it('falls back to HTTP and reuses the same client message ID for an explicit retry', async () => {
    vi.spyOn(chatClient, 'readMessages').mockResolvedValue({
      items: [],
      next_before: null,
      page_size: 50,
    })
    const persisted = message(
      '30000000-0000-4000-8000-000000000021',
      'self',
      'Retry me',
      '2026-10-01T08:04:00Z',
    )
    const sendHttp = vi
      .spyOn(chatClient, 'sendMessage')
      .mockRejectedValueOnce(new ApiError(0, 'network'))
      .mockResolvedValueOnce(persisted)
    renderChat()
    await screen.findByRole('heading', { name: 'Buddy chat' })

    fireEvent.change(screen.getByRole('textbox', { name: 'Message' }), {
      target: { value: 'Retry me' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('This message was not sent.')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() =>
      expect(screen.queryByText('This message was not sent.')).not.toBeInTheDocument(),
    )
    expect(screen.getByText('Retry me')).toBeVisible()
    expect(sendHttp).toHaveBeenCalledTimes(2)
    expect(sendHttp.mock.calls[0][0].clientMessageId).toBe(clientMessageId)
    expect(sendHttp.mock.calls[1][0].clientMessageId).toBe(clientMessageId)
  })

  it('keeps multiline Enter behavior, validates blank/Unicode overflow and exposes accessible composer help', async () => {
    vi.spyOn(chatClient, 'readMessages').mockResolvedValue({
      items: [],
      next_before: null,
      page_size: 50,
    })
    const sendHttp = vi.spyOn(chatClient, 'sendMessage')
    renderChat()
    await screen.findByRole('heading', { name: 'Buddy chat' })
    const composer = screen.getByRole('textbox', { name: 'Message' })

    fireEvent.change(composer, { target: { value: '   ' } })
    expect(screen.getByRole('alert')).toHaveTextContent('non-whitespace')
    fireEvent.keyDown(composer, { key: 'Enter' })
    expect(sendHttp).not.toHaveBeenCalled()

    fireEvent.change(composer, { target: { value: `${'🙂'.repeat(10_000)}a` } })
    expect(screen.getByRole('alert')).toHaveTextContent('10,000 Unicode characters')
    fireEvent.submit(composer.closest('form')!)
    expect(sendHttp).not.toHaveBeenCalled()
    expect(composer).toHaveAccessibleDescription(/Ctrl\+Enter/)
  })

  it('reconnects with bounded backoff, reconciles history and fails closed on authorization loss', async () => {
    const readHistory = vi.spyOn(chatClient, 'readMessages').mockResolvedValue({
      items: [],
      next_before: null,
      page_size: 50,
    })
    renderChat()
    await screen.findByRole('heading', { name: 'Buddy chat' })
    const first = FakeWebSocket.instances[0]
    act(() => first.ready())
    await screen.findByText('Live updates connected')
    const reconciliationsBeforeClose = readHistory.mock.calls.length

    vi.useFakeTimers()
    act(() => first.close(1013, 'CHAT_REALTIME_UNAVAILABLE'))
    expect(screen.getByRole('status')).toHaveTextContent('Reconnecting')
    act(() => vi.advanceTimersByTime(1_000))
    expect(FakeWebSocket.instances).toHaveLength(2)
    act(() => FakeWebSocket.instances[1].ready())
    vi.useRealTimers()
    await waitFor(() =>
      expect(readHistory.mock.calls.length).toBeGreaterThan(reconciliationsBeforeClose),
    )

    act(() => FakeWebSocket.instances[1].close(1008, 'CHAT_CONVERSATION_NOT_FOUND'))
    expect(await screen.findByRole('heading', { name: 'Conversation unavailable' })).toBeVisible()
    expect(screen.queryByRole('log')).not.toBeInTheDocument()
  })

  it('isolates state when the authenticated user opens another conversation', async () => {
    vi.spyOn(chatClient, 'readMessages').mockImplementation(async ({ conversationId: target }) => ({
      items: [
        message(
          target === conversationId
            ? '30000000-0000-4000-8000-000000000030'
            : '30000000-0000-4000-8000-000000000031',
          'buddy',
          target === conversationId ? 'First private chat' : 'Second private chat',
          '2026-10-01T08:05:00Z',
        ),
      ],
      next_before: null,
      page_size: 50,
    }))
    const view = renderChat()
    expect(await screen.findByText('First private chat')).toBeVisible()

    view.rerender(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <ChatConversation
            key={`${userId}:${secondConversationId}`}
            conversationId={secondConversationId}
            userId={userId}
          />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('Second private chat')).toBeVisible()
    expect(screen.queryByText('First private chat')).not.toBeInTheDocument()
  })
})
