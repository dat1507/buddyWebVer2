import { Component, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

function Unavailable() {
  const { t } = useTranslation()
  const [dismissed, setDismissed] = useState(false)
  return dismissed ? null : (
    <aside className="fixed bottom-24 right-4 z-40 max-w-[calc(100vw-2rem)] rounded-xl border bg-background p-4 text-sm text-foreground shadow-lg">
      <p role="status">{t('chatbot.errors.unavailable')}</p>
      <Button variant="ghost" onClick={() => setDismissed(true)}>
        {t('chatbot.close')}
      </Button>
    </aside>
  )
}

// A failed optional chunk must never take down the surrounding BuddyWeb application.
class ChatbotBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    return this.state.failed ? <Unavailable /> : this.props.children
  }
}

export { ChatbotBoundary }
