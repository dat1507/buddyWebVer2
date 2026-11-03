import { lazy, Suspense, useCallback, useEffect, useId, useRef, useState } from 'react'
import { MessageCircle, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { useChatbotConversation } from './use-chatbot-conversation'
import './chatbot.css'

const ChatbotPanel = lazy(() => import('./chatbot-panel'))

function ChatbotWidget() {
  const { t } = useTranslation()
  const [phase, setPhase] = useState<'closed' | 'open' | 'closing'>('closed')
  const open = phase === 'open'
  const panelReady = useRef(false)
  const restoreFocus = useRef(false)
  const launcher = useRef<HTMLButtonElement>(null)
  const id = useId()
  const conversation = useChatbotConversation()
  const ready = useCallback(() => {
    panelReady.current = true
  }, [])
  const exited = useCallback(() => {
    setPhase((current) => (current === 'closing' ? 'closed' : current))
  }, [])
  useEffect(() => {
    if (phase === 'closed') panelReady.current = false
  }, [phase])
  function close() {
    conversation.cancel()
    restoreFocus.current = true
    const focused = document.activeElement
    if (focused instanceof HTMLElement && focused.closest('.chatbot-container')) focused.blur()
    setPhase(panelReady.current ? 'closing' : 'closed')
  }
  useEffect(() => {
    if (open) {
      restoreFocus.current = false
      return
    }
    if (!restoreFocus.current) return
    // Runs after modal isolation cleanup. Reopening cancels stale focus restoration.
    const frame = requestAnimationFrame(() => {
      launcher.current?.focus({ preventScroll: true })
      restoreFocus.current = false
    })
    return () => cancelAnimationFrame(frame)
  }, [open])
  return (
    <>
      <Button
        ref={launcher}
        type="button"
        className="chatbot-launcher"
        size="icon"
        aria-label={t(open ? 'chatbot.close' : 'chatbot.open')}
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => (open ? close() : setPhase('open'))}
        onKeyDown={(event) => {
          if (open && event.key === 'Escape') close()
        }}
      >
        {open ? <X aria-hidden="true" /> : <MessageCircle aria-hidden="true" />}
      </Button>
      {phase !== 'closed' ? (
        <Suspense
          fallback={
            <div className="chatbot-loading" role="status">
              {t('chatbot.loadingPanel')}
              <Button variant="ghost" onClick={close}>
                {t('chatbot.close')}
              </Button>
            </div>
          }
        >
          <ChatbotPanel
            id={id}
            open={open}
            conversation={conversation}
            onClose={close}
            onReady={ready}
            onExited={exited}
          />
        </Suspense>
      ) : null}
    </>
  )
}

export default ChatbotWidget
