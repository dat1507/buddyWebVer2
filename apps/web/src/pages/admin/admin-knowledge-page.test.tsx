import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import {
  knowledgeClient,
  systemPromptUrl,
  type CatalogItem,
  type Faq,
  type FaqContent,
} from '@/features/admin-knowledge'
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
const row: CatalogItem = {
  id: faq.id,
  content,
  status: faq.status,
  managed: faq,
  builtin: null,
  sources: [],
}
const builtin: CatalogItem = {
  id: 'buddyweb-registration',
  content: {
    ...content,
    en: {
      questions: ['How do I register?', 'Create an account'],
      answer: 'Use the registration form.',
    },
    de: {
      questions: ['Wie registriere ich mich?'],
      answer: 'Verwende das Registrierungsformular.',
    },
    evidence: 'unsupported',
    source_title: '',
    source_url: '',
  },
  status: 'published',
  managed: null,
  builtin: null,
  sources: [{ title: 'Registration', reference: 'apps/web/src/pages/register.tsx' }],
}
builtin.builtin = {
  id: builtin.id,
  category: 'student-life',
  status: 'verified_code',
  en: 'How do I register?',
  de: 'Wie registriere ich mich?',
  content: builtin.content,
}

const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
const list = vi.spyOn(knowledgeClient, 'catalog')
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
  list.mockResolvedValue({ items: [row], has_more: false })
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

it('shows built-in and managed FAQs together with generic labels and complete bilingual details', async () => {
  list.mockResolvedValue({ items: [builtin, row], has_more: false })
  open()
  expect(await screen.findByText('How do I register?')).toBeVisible()
  expect(screen.getByText('What is the origami circle?')).toBeVisible()
  expect(screen.queryByText('Admin-managed')).not.toBeInTheDocument()
  fireEvent.click(screen.getAllByRole('button', { name: 'View FAQ' })[0])
  expect(screen.getByText('Use the registration form.')).toBeVisible()
  expect(screen.getByText('Verwende das Registrierungsformular.')).toBeVisible()
  expect(screen.getByText('Create an account')).toBeVisible()
  expect(screen.getByText('apps/web/src/pages/register.tsx')).toBeVisible()
  expect(screen.getByRole('heading', { name: 'View FAQ' })).toHaveFocus()
  fireEvent.click(screen.getByRole('button', { name: 'Close editor' }))
  await waitFor(() => expect(screen.getAllByRole('button', { name: 'View FAQ' })[0]).toHaveFocus())
})

it('prefills built-in bilingual questions, aliases and answers and saves only a linked draft', async () => {
  list.mockResolvedValue({ items: [builtin], has_more: false })
  save.mockResolvedValue({ ...faq, builtin_id: builtin.id, content: builtin.content })
  open()
  fireEvent.click(await screen.findByRole('button', { name: 'Edit FAQ' }))
  const en = within(screen.getByRole('group', { name: 'English' }))
  expect(en.getByLabelText('Main question')).toHaveValue('How do I register?')
  expect(en.getByLabelText('Alternative questions, one per line')).toHaveValue('Create an account')
  expect(en.getByLabelText('Answer')).toHaveValue('Use the registration form.')
  expect(
    within(screen.getByRole('group', { name: 'German' })).getByLabelText('Answer'),
  ).toHaveValue('Verwende das Registrierungsformular.')
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }))
  await screen.findByText('Changes saved.')
  expect(save).toHaveBeenCalledWith(null, builtin.content, builtin.id)
  expect(change).not.toHaveBeenCalled()
})

it('opens the linked saved draft instead of creating a second replacement', async () => {
  const linked = { ...faq, builtin_id: builtin.id }
  list.mockResolvedValue({
    items: [{ ...builtin, managed: linked, status: 'draft' }],
    has_more: false,
  })
  open()
  expect(await screen.findAllByRole('button', { name: 'Edit FAQ' })).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: 'Edit FAQ' }))
  expect(
    within(screen.getByRole('group', { name: 'English' })).getByLabelText('Answer'),
  ).toHaveValue('Fold paper.')
  save.mockResolvedValue(linked)
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }))
  await screen.findByText('Changes saved.')
  expect(save).toHaveBeenCalledWith(linked, linked.content, builtin.id)
})

it('sends bilingual/answer searches and filters together, resets pagination and clears all filters', async () => {
  list.mockResolvedValue({ items: [builtin], has_more: true })
  open()
  fireEvent.click(await screen.findByRole('button', { name: 'Next' }))
  await waitFor(() => expect(list.mock.lastCall?.[0].get('page')).toBe('2'))
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'REGISTRIERUNGSFORMULAR' } })
  fireEvent.click(screen.getByRole('button', { name: 'Search FAQs' }))
  fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'student-life' } })
  fireEvent.change(screen.getByLabelText('Publication status'), { target: { value: 'published' } })
  await waitFor(() => {
    const params = list.mock.lastCall![0]
    expect(Object.fromEntries(params)).toEqual({
      search: 'REGISTRIERUNGSFORMULAR',
      page: '1',
      category: 'student-life',
      status: 'published',
    })
  })
  fireEvent.click(screen.getByRole('button', { name: 'Clear search and filters' }))
  await waitFor(() =>
    expect(Object.fromEntries(list.mock.lastCall![0])).toEqual({ search: '', page: '1' }),
  )
})

it('retries errors without displaying a false empty result', async () => {
  list.mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ items: [], has_more: false })
  open()
  await screen.findByRole('alert')
  expect(screen.queryByText('No FAQs match these filters.')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('No FAQs match these filters.')).toBeVisible()
})

it('links only the read-only pinned repository guide with an explicit deployed-version caveat', async () => {
  vi.spyOn(knowledgeClient, 'references').mockResolvedValue({
    builtin: [],
    owner_guide: 'systemPrompt.txt',
  })
  open()
  fireEvent.click(screen.getByRole('button', { name: 'Reference Sources' }))
  const link = await screen.findByRole('link', { name: 'View systemPrompt.txt' })
  expect(link).toHaveAttribute('href', systemPromptUrl)
  expect(systemPromptUrl).toMatch(/blob\/[a-f0-9]{40}\/apps\/api.*systemPrompt\.txt$/)
  expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  expect(screen.getByText(/may differ from the deployed API version/)).toBeVisible()
})

it('localizes the unified list and bilingual detail in German', async () => {
  await i18n.changeLanguage('de')
  list.mockResolvedValue({ items: [builtin], has_more: false })
  open()
  expect(await screen.findByText('Wie registriere ich mich?')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'FAQ ansehen' }))
  expect(screen.getByText('Verwende das Registrierungsformular.')).toBeVisible()
})

it('shows published replacement provenance without transferring the original verification', async () => {
  const published = {
    ...faq,
    builtin_id: builtin.id,
    status: 'published' as const,
    published_revision: 1,
  }
  list.mockResolvedValue({
    items: [{ ...builtin, content: published.content, managed: published, status: 'published' }],
    has_more: false,
  })
  open()
  fireEvent.click(await screen.findByRole('button', { name: 'View FAQ' }))
  expect(screen.getByText('Fold paper.')).toBeVisible()
  expect(screen.getByText('Admin-provided public information')).toBeVisible()
  expect(screen.queryByText('Code verified')).not.toBeInTheDocument()
})
