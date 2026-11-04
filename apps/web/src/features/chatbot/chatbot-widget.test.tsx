import { StrictMode } from 'react'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import Widget from './chatbot-widget'
import i18n from '@/i18n'

const answer = {
  answer: 'Backend English fixture.',
  language: 'en',
  supported: true,
  status: 'answer',
  mode: 'local_retrieval',
  sources: [
    {
      entry_id: 'website-register',
      title: 'BuddyWeb guide',
      verification_status: 'verified_code',
      verified_on: '2026-10-22',
      references: [],
    },
  ],
}
const json = (value: unknown, status = 200, headers = {}) =>
  new Response(JSON.stringify(value), { status, headers })
let fetch: ReturnType<typeof vi.fn>
async function open() {
  fireEvent.click(screen.getByRole('button', { name: 'Open VGU Buddy Assistant' }))
  return await screen.findByRole('region', { name: 'VGU Buddy Assistant' })
}
function send(text = 'Fixture question?') {
  fireEvent.change(screen.getByRole('textbox', { name: 'Your question' }), {
    target: { value: text },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Send question' }))
}

describe('chatbot independent-question UI', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    vi.stubEnv('VITE_API_URL', '/api')
    fetch = vi.fn().mockImplementation(async () => json(answer))
    vi.stubGlobal('fetch', fetch)
  })
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it.each([
    ['en', 'Create an account', 'How do I register?'],
    ['de', 'Buddy finden', 'Wie funktioniert Buddy Matching?'],
  ])(
    'submits the %s localized suggestion through the existing transport',
    async (locale, label, question) => {
      await i18n.changeLanguage(locale)
      render(<Widget />)
      fireEvent.click(
        screen.getByRole('button', {
          name: locale === 'en' ? 'Open VGU Buddy Assistant' : 'VGU Buddy Assistant öffnen',
        }),
      )
      const suggestion = await screen.findByRole('button', { name: label })
      expect(fetch).not.toHaveBeenCalled()
      fireEvent.click(suggestion)
      await screen.findByText(answer.answer)
      expect(fetch).toHaveBeenCalledOnce()
      expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ question })
      expect(screen.getByRole('textbox')).toHaveFocus()
      expect(
        screen.queryByRole('group', { name: /Suggested questions|Fragevorschläge/ }),
      ).not.toBeInTheDocument()
    },
  )

  it('keeps suggested questions blocked after clearing a rate-limited conversation', async () => {
    fetch.mockImplementationOnce(async () => json({}, 429, { 'Retry-After': '60' }))
    render(<Widget />)
    await open()
    fireEvent.click(screen.getByRole('button', { name: 'Create an account' }))
    await screen.findByText(/A few too many questions/)
    fireEvent.click(screen.getByRole('button', { name: 'Clear conversation' }))
    expect(screen.getByRole('button', { name: 'Create an account' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Find a Buddy' })).toBeDisabled()
    expect(fetch).toHaveBeenCalledOnce()
  })

  it('starts closed without requests, focuses input, uses non-modal desktop semantics and restores focus', async () => {
    render(
      <StrictMode>
        <Widget />
      </StrictMode>,
    )
    expect(fetch).not.toHaveBeenCalled()
    const panel = await open()
    expect(panel).not.toHaveAttribute('aria-modal')
    expect(screen.getByRole('textbox')).toHaveFocus()
    expect(screen.getByText(/Each question is answered separately/)).toBeVisible()
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' })
    expect(screen.queryByRole('region', { name: 'VGU Buddy Assistant' })).not.toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Open VGU Buddy Assistant' })).toHaveFocus(),
    )
  })

  it('renders ordered turns, safe citations and preserves completed messages after close/reopen', async () => {
    render(<Widget />)
    await open()
    send('First question?')
    await screen.findByText(answer.answer)
    expect(screen.getByRole('log')).toHaveAttribute('aria-live', 'polite')
    expect(screen.getByRole('log')).toHaveAttribute('tabindex', '0')
    fireEvent.click(screen.getByText('1 source'))
    expect(screen.getByText(/website-register/)).toBeVisible()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    fetch.mockImplementationOnce(async () =>
      json({ ...answer, answer: 'Zweite Backend-Antwort.', language: 'de' }),
    )
    send('Zweite Frage?')
    const german = await screen.findByText('Zweite Backend-Antwort.')
    expect(german.parentElement).toHaveAttribute('lang', 'de')
    expect([...document.querySelectorAll('.chatbot-question')].map((el) => el.textContent)).toEqual(
      ['You: First question?', 'You: Zweite Frage?'],
    )
    fireEvent.click(
      within(screen.getByRole('region')).getByRole('button', { name: 'Close assistant' }),
    )
    await open()
    expect(screen.getByText(answer.answer)).toBeVisible()
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('renders backend text as text and approved external links with safe attributes', async () => {
    fetch.mockImplementationOnce(async () =>
      json({
        ...answer,
        answer: '<img src=x onerror=alert(1)>',
        sources: [
          { ...answer.sources[0], references: [{ title: 'VGU', url: 'https://vgu.edu.vn/' }] },
        ],
      }),
    )
    render(<Widget />)
    await open()
    send()
    expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeVisible()
    expect(document.querySelector('.chatbot-answer img')).toBeNull()
    fireEvent.click(screen.getByText('1 source'))
    const link = screen.getByRole('link', { name: /VGU/ })
    expect(link).toHaveAttribute('href', 'https://vgu.edu.vn/')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveAttribute('referrerpolicy', 'no-referrer')
  })

  it('validates blank/long input, Shift+Enter and composition without sending', async () => {
    render(<Widget />)
    await open()
    const textbox = screen.getByRole('textbox')
    expect(screen.getByRole('button', { name: 'Send question' })).toBeDisabled()
    fireEvent.change(textbox, { target: { value: 'a'.repeat(501) } })
    expect(textbox).toHaveAttribute('aria-invalid', 'true')
    fireEvent.keyDown(textbox, { key: 'Enter' })
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.change(textbox, { target: { value: 'Fixture question?' } })
    fireEvent.keyDown(textbox, { key: 'Enter', shiftKey: true })
    fireEvent.keyDown(textbox, { key: 'Enter', isComposing: true })
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.keyDown(textbox, { key: 'Enter' })
    await screen.findByText(answer.answer)
    expect(fetch).toHaveBeenCalledOnce()
  })

  it('prevents duplicate submissions while pending and does not erase the next draft', async () => {
    let finish!: (value: Response) => void
    fetch.mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          finish = resolve
        }),
    )
    render(<Widget />)
    await open()
    send()
    expect(screen.getByText('Looking up public information…')).toBeVisible()
    const textbox = screen.getByRole('textbox')
    fireEvent.keyDown(textbox, { key: 'Enter' })
    fireEvent.keyDown(textbox, { key: 'Enter' })
    fireEvent.change(textbox, { target: { value: 'Next question?' } })
    fireEvent.keyDown(textbox, { key: 'Enter' })
    expect(fetch).toHaveBeenCalledOnce()
    await act(async () => finish(json(answer)))
    expect(textbox).toHaveValue('Next question?')
  })

  it.each(['insufficient', 'choose_language', 'restricted'])(
    'shows a valid %s fallback without an error/retry',
    async (status) => {
      fetch.mockImplementationOnce(async () =>
        json({ ...answer, supported: false, sources: [], status, answer: 'Backend fallback.' }),
      )
      render(<Widget />)
      await open()
      send()
      expect(await screen.findByText('Backend fallback.')).toBeVisible()
      expect(screen.queryByRole('button', { name: 'Retry question' })).not.toBeInTheDocument()
    },
  )

  it.each([
    [400, /1–500/],
    [422, /1–500/],
    [503, /temporarily unavailable/],
    [504, /took too long/],
    [500, /Something went wrong/],
  ])('shows a localized safe error for HTTP %s', async (status, message) => {
    fetch.mockImplementationOnce(async () =>
      json({ status: 'disabled', answer: 'raw private diagnostic' }, status as number),
    )
    render(<Widget />)
    await open()
    send()
    expect(await screen.findByText(message as RegExp)).toBeVisible()
    expect(screen.queryByText('raw private diagnostic')).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledOnce()
  })

  it('allows manual network retry without duplicating the question', async () => {
    fetch.mockRejectedValueOnce(new Error('sensitive diagnostics'))
    render(<Widget />)
    await open()
    send()
    await screen.findByText(/couldn’t connect/)
    fireEvent.click(screen.getByRole('button', { name: 'Retry question' }))
    await screen.findByText(answer.answer)
    expect(screen.getAllByText('Fixture question?')).toHaveLength(1)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('respects Retry-After across clear without any automatic retry', async () => {
    render(<Widget />)
    await open()
    vi.useFakeTimers()
    fetch.mockImplementationOnce(async () =>
      json({ status: 'rate_limited' }, 429, { 'Retry-After': '2' }),
    )
    await act(async () => send())
    expect(screen.getByRole('button', { name: 'Retry question' })).toBeDisabled()
    expect(screen.getByText(/Please wait 2 seconds/)).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Clear conversation' }))
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Another?' } })
    expect(screen.getByRole('button', { name: 'Send question' })).toBeDisabled()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000)
    })
    expect(screen.getByRole('button', { name: 'Send question' })).toBeEnabled()
    expect(fetch).toHaveBeenCalledOnce()
  })

  it('cancels on close and ignores an old response after a retry', async () => {
    let finish!: (value: Response) => void
    fetch.mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          finish = resolve
        }),
    )
    render(<Widget />)
    await open()
    send()
    const signal = fetch.mock.calls[0][1].signal as AbortSignal
    fireEvent.click(
      within(screen.getByRole('region')).getByRole('button', { name: 'Close assistant' }),
    )
    expect(signal.aborted).toBe(true)
    await open()
    fireEvent.click(screen.getByRole('button', { name: 'Retry question' }))
    await screen.findByText(answer.answer)
    await act(async () => finish(json({ ...answer, answer: 'Stale reply.' })))
    expect(screen.queryByText('Stale reply.')).not.toBeInTheDocument()
    expect(screen.getAllByText('Fixture question?')).toHaveLength(1)
  })

  it('cleans up an in-flight request on unmount', async () => {
    fetch.mockImplementationOnce(() => new Promise(() => undefined))
    const view = render(<Widget />)
    await open()
    send()
    const signal = fetch.mock.calls[0][1].signal as AbortSignal
    view.unmount()
    expect(signal.aborted).toBe(true)
  })

  it('localizes the UI without overriding backend reply language', async () => {
    await i18n.changeLanguage('de')
    render(<Widget />)
    fireEvent.click(screen.getByRole('button', { name: 'VGU Buddy Assistant öffnen' }))
    await screen.findByRole('textbox', { name: 'Deine Frage' })
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'English fixture?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Frage senden' }))
    const reply = await screen.findByText(answer.answer)
    expect(reply.parentElement).toHaveAttribute('lang', 'en')
    expect(screen.getByText(/Jede Frage wird einzeln beantwortet/)).toBeVisible()
  })

  it('uses modal semantics, isolation, scroll lock and focus wrapping only on mobile', async () => {
    vi.spyOn(window, 'matchMedia').mockImplementation(
      (query) =>
        ({
          matches: query === '(max-width: 639px)',
          media: query,
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
        }) as unknown as MediaQueryList,
    )
    render(
      <>
        <button>Outside</button>
        <Widget />
      </>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Open VGU Buddy Assistant' }))
    const dialog = await screen.findByRole('dialog', { name: 'VGU Buddy Assistant' })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(document.body.style.overflow).toBe('hidden')
    expect(screen.getByText('Outside').closest('[inert]')).toBeTruthy()
    const first = within(dialog).getByRole('button', { name: 'Clear conversation' })
    first.focus()
    fireEvent.keyDown(first, { key: 'Tab', shiftKey: true })
    expect(screen.getByRole('textbox')).toHaveFocus()
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' })
    expect(document.body.style.overflow).toBe('')
    expect(screen.getByText('Outside').closest('[inert]')).toBeNull()
  })
  it('keeps the inert exit mounted until its own animation ends and ignores stale events after reopening', async () => {
    const style = window.getComputedStyle.bind(window)
    vi.spyOn(window, 'getComputedStyle').mockImplementation((element) => {
      const original = style(element)
      return element.classList.contains('chatbot-panel')
        ? Object.assign(original, { animationDuration: '180ms', animationDelay: '0s' })
        : original
    })
    render(<Widget />)
    const panel = await open()
    const container = panel.parentElement!
    expect(container).toHaveAttribute('data-state', 'open')
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' })
    expect(container).toHaveAttribute('data-state', 'closing')
    expect(container).toHaveAttribute('inert')
    expect(container).toHaveAttribute('aria-hidden', 'true')
    expect(within(container).getByRole('log', { hidden: true })).toHaveAttribute('aria-live', 'off')
    expect(screen.queryByRole('region')).not.toBeInTheDocument()
    fireEvent(
      panel,
      Object.assign(new Event('animationend', { bubbles: true }), { animationName: 'unrelated' }),
    )
    expect(panel).toBeInTheDocument()
    await open()
    expect(screen.getByRole('textbox')).toHaveFocus()
    fireEvent(
      panel,
      Object.assign(new Event('animationend', { bubbles: true }), {
        animationName: 'chatbot-exit',
      }),
    )
    expect(screen.getByRole('region')).toBeInTheDocument()
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' })
    fireEvent(
      panel,
      Object.assign(new Event('animationend', { bubbles: true }), {
        animationName: 'chatbot-exit',
      }),
    )
    expect(container).not.toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Open VGU Buddy Assistant' })).toHaveFocus(),
    )
  })

  it.each([
    ['180ms', 230],
    ['0s', 0],
  ])(
    'cleans up without animationend for duration %s (including reduced motion)',
    async (duration, timeout) => {
      const style = window.getComputedStyle.bind(window)
      vi.spyOn(window, 'getComputedStyle').mockImplementation((element) =>
        Object.assign(style(element), { animationDuration: duration, animationDelay: '0s' }),
      )
      render(<Widget />)
      const panel = await open()
      vi.useFakeTimers()
      fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' })
      expect(panel).toBeInTheDocument()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(timeout as number)
      })
      expect(panel).not.toBeInTheDocument()
      expect(document.querySelector('.chatbot-container')).toBeNull()
      expect(screen.getByRole('button', { name: 'Open VGU Buddy Assistant' })).toHaveAttribute(
        'aria-expanded',
        'false',
      )
    },
  )

  it('renders the real historical contract with qualification and no false verification date', async () => {
    fetch.mockImplementationOnce(async () =>
      json({
        ...answer,
        answer:
          'The previous student guide mentions EVA Laundry. Current availability has not been confirmed.',
        status: 'historical_reference',
        sources: [
          {
            entry_id: 'legacy-laundry',
            title: 'Historical student guide (systemPrompt.txt)',
            verification_status: 'historical_reference',
            verified_on: null,
            references: [],
          },
        ],
      }),
    )
    render(<Widget />)
    await open()
    send('Where is the laundry service?')
    expect(await screen.findByText(/Current availability has not been confirmed/)).toBeVisible()
    expect(screen.getByText('Historical reference — current status unconfirmed')).toBeVisible()
    fireEvent.click(screen.getByText('1 source'))
    expect(screen.getByText('Previous student guide (systemPrompt.txt)')).toBeVisible()
    expect(screen.getByText(/legacy-laundry · Not currently verified/)).toBeVisible()
    expect(screen.queryByText(/Verified/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
  it('does not move focus when the initially closed optional widget mounts', async () => {
    vi.useFakeTimers()
    const outside = document.createElement('button')
    document.body.append(outside)
    outside.focus()
    render(<Widget />)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(32)
    })
    expect(outside).toHaveFocus()
    outside.remove()
  })
  it.each(['owner_provided', 'conflicted'])(
    'renders canonical %s qualification and version/line citation safely',
    async (status) => {
      fetch.mockImplementationOnce(async () =>
        json({
          ...answer,
          status,
          answer: 'Conditional fixture interpretation. Original source passage follows.',
          sources: [
            {
              entry_id: 'owner-' + 'a'.repeat(20),
              title: 'Owner-provided guide (systemPrompt.txt)',
              verification_status: status,
              verified_on: null,
              references: [],
              provenance: {
                filename: 'systemPrompt.txt',
                sha256: 'b'.repeat(64),
                start_line: 10,
                end_line: 12,
                section: 'Fixture section',
              },
            },
          ],
        }),
      )
      render(<Widget />)
      await open()
      send('Fixture topic?')
      expect(await screen.findByText(/Conditional fixture interpretation/)).toBeVisible()
      expect(
        screen.getByText(
          status === 'conflicted'
            ? 'Conflicting source information'
            : 'Owner-provided guide — current status unconfirmed',
        ),
      ).toBeVisible()
      fireEvent.click(screen.getByText('1 source'))
      expect(screen.getByText('Owner-provided guide (systemPrompt.txt)')).toBeVisible()
      expect(screen.getByText(/Lines 10–12 · Source bbbbbbbbbbbb/)).toBeVisible()
      expect(screen.queryByRole('link')).not.toBeInTheDocument()
      expect(screen.queryByText(/Verified on/)).not.toBeInTheDocument()
    },
  )
  it('renders question, answer and citation markup as text without executing HTML', async () => {
    const question = '<script data-chatbot-injection>synthetic()</script>'
    const reply = '<img src=x onerror="synthetic()">'
    const title = '<svg onload="synthetic()">'
    fetch.mockImplementationOnce(async () =>
      json({
        ...answer,
        answer: reply,
        sources: [
          {
            ...answer.sources[0],
            references: [{ title, url: 'https://vgu.edu.vn/' }],
          },
        ],
      }),
    )
    render(<Widget />)
    await open()
    send(question)
    expect(await screen.findByText(reply)).toBeVisible()
    expect(screen.getByText(question)).toBeVisible()
    fireEvent.click(screen.getByText('1 source'))
    expect(screen.getByRole('link', { name: /synthetic/ })).toHaveTextContent(title)
    expect(document.querySelector('script[data-chatbot-injection]')).toBeNull()
    expect(document.querySelector('.chatbot-message img')).toBeNull()
  })
})
