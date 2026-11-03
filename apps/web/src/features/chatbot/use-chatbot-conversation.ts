import { useEffect, useRef, useState } from 'react'

import { chatbotClient, validQuestion, type ChatbotAnswer } from './chatbot-client'
import { ApiError, normalizeApiError } from '@/lib/api'

interface Turn {
  id: number
  question: string
  status: 'pending' | 'done' | 'failed'
  reply?: ChatbotAnswer
  error?: ApiError
}

function useChatbotConversation() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [blockedUntil, setBlockedUntil] = useState(0)
  const [now, setNow] = useState(Date.now)
  const active = useRef<{ id: number; controller: AbortController } | null>(null)
  const serial = useRef(0)
  const blocked = useRef(0)
  const pending = turns.some((turn) => turn.status === 'pending')
  const retrySeconds = Math.max(0, Math.ceil((blockedUntil - now) / 1000))
  const coolingDown = retrySeconds > 0

  useEffect(() => {
    if (!coolingDown) return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [blockedUntil, coolingDown])

  useEffect(
    () => () => {
      active.current?.controller.abort()
      active.current = null
    },
    [],
  )

  function cancel() {
    const request = active.current
    if (!request) return
    active.current = null
    request.controller.abort()
    setTurns((previous) =>
      previous.map((turn) =>
        turn.id === request.id
          ? { ...turn, status: 'failed', error: new ApiError(0, 'cancelled') }
          : turn,
      ),
    )
  }

  async function send(question: string, retryId?: number) {
    if (active.current || Date.now() < blocked.current || !validQuestion(question)) return
    const id = retryId ?? ++serial.current
    const request = { id, controller: new AbortController() }
    active.current = request // synchronous fence against repeated clicks/Enter before React commits
    setTurns((previous) =>
      retryId === undefined
        ? [...previous.slice(-19), { id, question, status: 'pending' }]
        : previous.map((turn) => (turn.id === id ? { id, question, status: 'pending' } : turn)),
    )
    if (retryId === undefined) setDraft('')
    try {
      const reply = await chatbotClient.ask(question, request.controller.signal)
      if (active.current !== request) return
      setTurns((previous) =>
        previous.map((turn) => (turn.id === id ? { id, question, status: 'done', reply } : turn)),
      )
    } catch (failure) {
      if (active.current !== request) return
      const error = normalizeApiError(failure)
      if (
        error.status === 429 ||
        (error.retryAfter !== null && [503, 504].includes(error.status))
      ) {
        const seconds =
          error.retryAfter !== null && Number.isFinite(error.retryAfter)
            ? Math.max(1, Math.min(86400, error.retryAfter))
            : 60
        blocked.current = Date.now() + seconds * 1000
        setBlockedUntil(blocked.current)
        setNow(Date.now())
      }
      setTurns((previous) =>
        previous.map((turn) => (turn.id === id ? { id, question, status: 'failed', error } : turn)),
      )
    } finally {
      if (active.current === request) active.current = null
    }
  }

  function clear() {
    cancel()
    setTurns([])
    setDraft('')
  }

  return { turns, draft, setDraft, pending, retrySeconds, send, cancel, clear }
}

export { useChatbotConversation }
export type { Turn }
