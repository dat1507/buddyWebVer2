import '@/i18n'
import i18n from '@/i18n'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'
import { RetentionNotice, EvictionNotice } from './retention-notice'
const removed = [
  {
    id: '11111111-1111-4111-8111-111111111111',
    title_en: 'Welcome Day',
    title_de: 'Willkommenstag',
  },
]
afterEach(async () => {
  await i18n.changeLanguage('en')
})
describe('Rolling9 publication feedback', () => {
  it.each(['en', 'de'])(
    'warns about permanent retention and identifies evicted memory in %s',
    async (language) => {
      await i18n.changeLanguage(language)
      render(
        <>
          <RetentionNotice />
          <EvictionNotice items={removed} pending={false} />
        </>,
      )
      expect(screen.getByText(/9/)).toBeVisible()
      expect(screen.getByRole('status')).toHaveTextContent(
        language === 'de' ? 'Willkommenstag' : 'Welcome Day',
      )
      expect(screen.queryByRole('dialog')).toBeNull()
    },
  )
  it('reports pending physical cleanup instead of claiming complete deletion', () => {
    render(<EvictionNotice items={removed} pending />)
    expect(screen.getByRole('status')).toHaveTextContent(i18n.t('recaps.cleanup'))
  })
  it('does not announce an eviction when nothing was evicted', () => {
    render(<EvictionNotice items={[]} pending={false} />)
    expect(screen.queryByRole('status')).toBeNull()
  })
})
