import '@/i18n'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
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
    expect(screen.getAllByRole('img')).toHaveLength(2)
  })
})
