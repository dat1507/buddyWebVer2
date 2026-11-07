import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { knowledgeClient, type Faq, type FaqContent } from '@/features/admin-knowledge'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { AdminKnowledgePage } from '@/pages/admin/admin-knowledge-page'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'admin@example.invalid',
  role: 'ADMIN' as const,
  email_verified: true,
}
const content: FaqContent = {
  category: 'student-life',
  en: { questions: ['What is the origami circle?'], answer: 'Fold paper.' },
  de: { questions: ['Was ist der Origami-Kreis?'], answer: 'Papier falten.' },
  source_title: 'VGU',
  source_url: 'https://vgu.edu.vn/',
  evidence: 'admin_managed',
}
const faq: Faq = {
  id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  builtin_id: null,
  version: 1,
  draft_revision: 1,
  published_revision: null,
  published_at: null,
  updated_at: '2026-11-07T00:00:00Z',
  status: 'draft',
  content,
}
const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
const list = vi.spyOn(knowledgeClient, 'list')
const save = vi.spyOn(knowledgeClient, 'save')
const change = vi.spyOn(knowledgeClient, 'change')
const preview = vi.spyOn(knowledgeClient, 'preview')
const history = vi.spyOn(knowledgeClient, 'history')
const detail = vi.spyOn(knowledgeClient, 'detail')

function open() {
  render(
    <QueryClientProvider client={client}>
      <AdminKnowledgePage />
    </QueryClientProvider>,
  )
}

beforeEach(async () => {
  await i18n.changeLanguage('en')
  useAuthStore.getState().setAuthenticated(user)
  list.mockResolvedValue({ items: [faq], has_more: false })
  history.mockResolvedValue({
    items: [{ revision: 1, author_id: user.id, created_at: faq.updated_at, content }],
    has_more: false,
  })
})

afterEach(() => {
  cleanup()
  client.clear()
  vi.resetAllMocks()
  useAuthStore.getState().resetSession()
})

it('creates an incomplete draft and displays real preview selection without publishing', async () => {
  save.mockResolvedValue(faq)
  preview.mockResolvedValue({
    question: 'What is the origami circle?',
    selected: 'existing',
    issue: 'retrieval_conflict',
    answer: {
      answer: 'Existing answer',
      language: 'en',
      supported: false,
      status: 'insufficient',
      sources: [],
      mode: 'local_retrieval',
    },
  })
  open()
  fireEvent.click(screen.getByRole('button', { name: 'New FAQ' }))
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }))
  await screen.findByText('Changes saved.')
  expect(save).toHaveBeenCalledWith(
    null,
    expect.objectContaining({ evidence: 'unsupported' }),
    null,
  )
  fireEvent.change(screen.getByLabelText('Test question'), {
    target: { value: 'What is the origami circle?' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
  expect(await screen.findByText('Existing answer')).toBeVisible()
  expect(screen.getByText(/Existing source selected/)).toBeVisible()
  expect(change).not.toHaveBeenCalled()
})

it('confirms publish, unpublish and public revision restore', async () => {
  const published = {
    ...faq,
    status: 'published' as const,
    version: 2,
    published_revision: 1,
    published_at: faq.updated_at,
  }
  const unpublished = {
    ...published,
    status: 'unpublished' as const,
    version: 3,
    published_revision: null,
  }
  change
    .mockResolvedValueOnce(published)
    .mockResolvedValueOnce(unpublished)
    .mockResolvedValueOnce(published)
  open()
  fireEvent.click(await screen.findByRole('button', { name: 'Edit FAQ' }))
  for (const name of ['Publish', 'Unpublish']) {
    fireEvent.click(await screen.findByRole('button', { name: new RegExp('^' + name + '$') }))
    const dialog = screen.getByRole('alertdialog', { name })
    expect(change).toHaveBeenCalledTimes(name === 'Publish' ? 0 : 1)
    fireEvent.click(within(dialog).getByRole('button', { name: /^Confirm$/ }))
    await waitFor(() => expect(dialog).not.toBeInTheDocument())
  }
  fireEvent.click(screen.getByRole('button', { name: 'Revision history' }))
  const action = 'Restore and publish'
  fireEvent.click(await screen.findByRole('button', { name: action }))
  fireEvent.click(
    within(screen.getByRole('alertdialog', { name: action })).getByRole('button', {
      name: 'Confirm',
    }),
  )
  await waitFor(() =>
    expect(change).toHaveBeenLastCalledWith(unpublished, {
      action: 'restore',
      revision: 1,
      publish: true,
    }),
  )
})

it('preserves a stale edit until an Admin explicitly loads the current draft', async () => {
  save.mockRejectedValue(new ApiError(409, 'conflict', null, 'stale_version'))
  detail.mockResolvedValue({ ...faq, version: 2 })
  open()
  fireEvent.click(await screen.findByRole('button', { name: 'Edit FAQ' }))
  const answer = within(screen.getByRole('group', { name: 'English' })).getByLabelText('Answer')
  fireEvent.change(answer, { target: { value: 'Unsaved local edit' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Another Admin saved a newer version')
  expect(answer).toHaveValue('Unsaved local edit')
  fireEvent.click(screen.getByRole('button', { name: 'Open latest saved draft' }))
  await screen.findByText('Latest saved draft loaded.')
  expect(answer).toHaveValue('Fold paper.')
})
