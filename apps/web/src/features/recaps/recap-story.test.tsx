import '@/i18n'
import i18n from '@/i18n'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RecapStory } from './recap-story'
import type { Recap } from './recaps'
vi.mock('./recap-photo', () => ({
  RecapImage: ({ photo, display }: { photo: { alt_en: string }; display?: boolean }) => (
    <img src={display ? 'display.webp' : 'thumbnail.webp'} alt={photo.alt_en} />
  ),
}))
const recap: Recap = {
  id: '11111111-1111-4111-8111-111111111111',
  related_event_id: null,
  title_en: 'Together',
  title_de: 'Zusammen',
  summary_en: 'Our day',
  summary_de: 'Unser Tag',
  editorial_en: null,
  editorial_de: null,
  event_date: null,
  status: 'PUBLISHED',
  version: 1,
  thumbnail_id: null,
  cleanup_pending: false,
  photos: [0, 1].map((sort_order) => ({
    id: `22222222-2222-4222-8222-22222222222${sort_order}`,
    alt_en: `Friends ${sort_order}`,
    alt_de: `Freunde ${sort_order}`,
    caption_en: null,
    caption_de: null,
    width: 800,
    height: 600,
    sort_order,
  })),
}
describe('Recap story', () => {
  afterEach(async () => {
    await i18n.changeLanguage('en')
  })
  it('loads full images only in the keyboard-controlled modal and restores focus', async () => {
    render(
      <MemoryRouter>
        <RecapStory recap={recap} />
      </MemoryRouter>,
    )
    expect(document.querySelector('[src="display.webp"]')).toBeNull()
    const opener = screen.getAllByRole('button', { name: /Open photo 1/ })[0]
    opener.focus()
    fireEvent.click(opener)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(document.querySelector('[src="display.webp"]')).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'ArrowRight' })
    expect(screen.getByRole('status')).toHaveTextContent('2 / 2')
    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(opener).toHaveFocus()
  })
  it('renders a complete photo-focused page with one photo and no date/editorial', () => {
    render(
      <MemoryRouter>
        <RecapStory recap={{ ...recap, photos: recap.photos.slice(0, 1) }} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { level: 1, name: 'Together' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Full Photo Gallery' })).toBeInTheDocument()
    expect(screen.getAllByRole('img')).toHaveLength(1)
  })
  it.each(['en', 'de'])(
    'renders every ordered photo once, captions and multiline copy in %s',
    async (language) => {
      await i18n.changeLanguage(language)
      const photos = Array.from({ length: 12 }, (_, index) => ({
        ...recap.photos[0],
        id: `22222222-2222-4222-8222-${String(index).padStart(12, '0')}`,
        sort_order: index,
        alt_en: `Moment ${index}`,
        alt_de: `Augenblick ${index}`,
        caption_en: `Caption ${index}`,
        caption_de: `Bildtext ${index}`,
      }))
      const { container } = render(
        <MemoryRouter>
          <RecapStory
            recap={{
              ...recap,
              photos,
              event_date: '2026-11-04',
              summary_en: 'Our day\nTogether',
              summary_de: 'Unser Tag\nZusammen',
              editorial_en: 'First paragraph\nSecond paragraph',
              editorial_de: 'Erster Absatz\nZweiter Absatz',
            }}
          />
        </MemoryRouter>,
      )
      expect(screen.queryByRole('heading', { name: i18n.t('recaps.highlights') })).toBeNull()
      expect(screen.getAllByRole('img')).toHaveLength(12)
      const buttons = screen.getAllByRole('button', {
        name: new RegExp(i18n.t('recaps.openPhoto')),
      })
      expect(buttons.map((button) => button.getAttribute('aria-label'))).toEqual(
        photos.map(
          (photo, index) =>
            `${i18n.t('recaps.openPhoto')} ${index + 1}: ${language === 'de' ? photo.alt_de : photo.alt_en}`,
        ),
      )
      expect(container.querySelector('.recap-detail-copy > p')?.textContent).toBe(
        language === 'de' ? 'Unser Tag\nZusammen' : 'Our day\nTogether',
      )
      expect(container.querySelector('.recap-editorial')?.textContent).toBe(
        language === 'de' ? 'Erster Absatz\nZweiter Absatz' : 'First paragraph\nSecond paragraph',
      )
      expect(screen.getByText(language === 'de' ? 'Bildtext 11' : 'Caption 11')).toBeVisible()
      fireEvent.click(buttons[11])
      expect(screen.getByRole('status')).toHaveTextContent('12 / 12')
      fireEvent.click(screen.getByRole('button', { name: i18n.t('recaps.next') }))
      expect(screen.getByRole('status')).toHaveTextContent('1 / 12')
      fireEvent.click(screen.getByRole('button', { name: i18n.t('recaps.previous') }))
      expect(screen.getByRole('status')).toHaveTextContent('12 / 12')
      fireEvent.keyDown(document, { key: 'Escape' })
      await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    },
  )
})
