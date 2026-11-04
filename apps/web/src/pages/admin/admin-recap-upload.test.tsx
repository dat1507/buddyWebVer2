import '@/i18n'
import i18n from '@/i18n'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import * as recaps from '@/features/recaps/recaps'
import { adminEventsClient } from '@/features/admin-events/admin-events'
import { sessionClient } from '@/features/auth/session-client'
import { AdminRecapEditorPage } from './admin-recap-pages'

vi.mock('@/features/recaps/recap-photo', () => ({
  RecapImage: () => <img alt="Synthetic uploaded photo" />,
}))

const record: recaps.Recap = {
  id: '11111111-1111-4111-8111-111111111111',
  related_event_id: null,
  title_en: 'Synthetic upload check',
  title_de: 'Synthetischer Uploadtest',
  summary_en: null,
  summary_de: null,
  editorial_en: null,
  editorial_de: null,
  event_date: null,
  status: 'DRAFT',
  version: 1,
  thumbnail_id: null,
  photos: [],
  cleanup_pending: false,
}
const uploaded: recaps.Recap = {
  ...record,
  version: 3,
  photos: [
    {
      id: '22222222-2222-4222-8222-222222222222',
      alt_en: 'Synthetic photo',
      alt_de: 'Synthetisches Foto',
      caption_en: null,
      caption_de: null,
      width: 640,
      height: 480,
      sort_order: 0,
    },
  ],
}
const image = () => new File(['synthetic image bytes'], 'synthetic.png', { type: 'image/png' })

beforeEach(async () => {
  await i18n.changeLanguage('en')
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:synthetic')
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  vi.spyOn(adminEventsClient, 'readEvents').mockResolvedValue({
    items: [],
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  })
  vi.spyOn(recaps, 'fetchRecap').mockResolvedValue(record)
  vi.spyOn(recaps, 'mutateRecap').mockResolvedValue({ ...record, version: 2 })
  vi.spyOn(sessionClient, 'authenticatedJson').mockImplementation(async () => {
    vi.mocked(recaps.fetchRecap).mockResolvedValue(uploaded)
    return uploaded
  })
})
afterEach(async () => {
  vi.restoreAllMocks()
  await i18n.changeLanguage('en')
})

function CurrentRoute() {
  return <output aria-label="Current route">{useLocation().pathname}</output>
}

function editor(fresh = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={[
          fresh ? '/admin/events/recaps/new' : `/admin/events/recaps/${record.id}/edit`,
        ]}
      >
        <CurrentRoute />
        <Routes>
          <Route path="/admin/events/recaps/new" element={<AdminRecapEditorPage />} />
          <Route path="/admin/events/recaps/:recapId/edit" element={<AdminRecapEditorPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
async function input() {
  return (await screen.findByLabelText(i18n.t('recaps.upload'))) as HTMLInputElement
}
function select(input: HTMLInputElement, file = image()) {
  fireEvent.change(input, { target: { files: [file] } })
}

it('enables the native file input for a new draft and saves before uploading to its ID', async () => {
  editor(true)
  const picker = await input()
  expect(picker).toBeEnabled()
  const click = vi.fn()
  picker.addEventListener('click', click)
  fireEvent.click(picker)
  expect(click).toHaveBeenCalledOnce()
  const file = image()
  select(picker, file)
  await screen.findByAltText('Synthetic uploaded photo')
  expect(recaps.mutateRecap).toHaveBeenCalledWith(
    '',
    'POST',
    expect.objectContaining({ related_event_id: null }),
  )
  expect(sessionClient.authenticatedJson).toHaveBeenCalledWith(
    expect.stringMatching(new RegExp(`^/admin/recaps/${record.id}/photos\\?upload_id=`)),
    expect.objectContaining({ method: 'POST', formData: expect.any(FormData) }),
  )
  const [, request] = vi.mocked(sessionClient.authenticatedJson).mock.calls[0]
  expect(request?.formData?.get('version')).toBe('2')
  expect(request?.formData?.get('file')).toBe(file)
  expect(vi.mocked(recaps.mutateRecap).mock.invocationCallOrder[0]).toBeLessThan(
    vi.mocked(sessionClient.authenticatedJson).mock.invocationCallOrder[0],
  )
})

it.each(['en', 'de'])(
  'accepts a drop with unsaved content and preserves it in %s',
  async (language) => {
    await i18n.changeLanguage(language)
    editor()
    const picker = await input()
    fireEvent.change(screen.getByLabelText(`${i18n.t('recaps.title')} · EN`), {
      target: { value: 'Edited title' },
    })
    expect(picker).toBeEnabled()
    fireEvent.drop(picker.closest('div')!, { dataTransfer: { files: [image()] } })
    await screen.findByAltText('Synthetic uploaded photo')
    expect(recaps.mutateRecap).toHaveBeenCalledWith(
      `/${record.id}`,
      'PUT',
      expect.objectContaining({ title_en: 'Edited title', version: 1 }),
    )
  },
)

it.each([
  new File(['text'], 'invalid.txt', { type: 'text/plain' }),
  new File([], 'empty.png', { type: 'image/png' }),
  new File([new Uint8Array(5 * 1024 * 1024 + 1)], 'large.png', { type: 'image/png' }),
])('rejects invalid files without saving or uploading: $name', async (file) => {
  editor(true)
  select(await input(), file)
  expect(await screen.findByRole('alert')).toHaveTextContent(i18n.t('recaps.uploadInvalid'))
  expect(recaps.mutateRecap).not.toHaveBeenCalled()
  expect(sessionClient.authenticatedJson).not.toHaveBeenCalled()
})

it('shows an upload error rather than announcing successful completion', async () => {
  vi.mocked(sessionClient.authenticatedJson).mockRejectedValue(new Error('synthetic failure'))
  editor()
  select(await input())
  expect(await screen.findByRole('alert')).toHaveTextContent(i18n.t('recaps.uploadFailed'))
  expect(await screen.findByRole('button', { name: i18n.t('recaps.retry') })).toBeEnabled()
  expect(screen.queryByText(i18n.t('recaps.uploadDone'))).toBeNull()
})

it('does not upload if draft saving fails', async () => {
  vi.mocked(recaps.mutateRecap).mockRejectedValue(new Error('synthetic save failure'))
  editor(true)
  select(await input())
  expect(await screen.findByRole('alert')).toHaveTextContent(i18n.t('recaps.mutationError'))
  expect(sessionClient.authenticatedJson).not.toHaveBeenCalled()
})

it('retains a newly saved draft and failed file for retry without creating a duplicate', async () => {
  vi.mocked(sessionClient.authenticatedJson).mockRejectedValueOnce(new Error('synthetic failure'))
  editor(true)
  select(await input())
  expect(await screen.findByRole('alert')).toHaveTextContent(i18n.t('recaps.uploadFailed'))
  fireEvent.click(await screen.findByRole('button', { name: i18n.t('recaps.retry') }))
  // Successful retry replaces /new with the saved editor, remounting the image.
  // Assert the final route and fresh DOM together instead of retaining the old img node.
  await waitFor(() => {
    expect(screen.getByLabelText('Current route')).toHaveTextContent(
      `/admin/events/recaps/${record.id}/edit`,
    )
    expect(screen.getByAltText('Synthetic uploaded photo')).toBeVisible()
    expect(screen.getByLabelText(`${i18n.t('recaps.alt')} · EN · 1`)).toHaveValue('Synthetic photo')
  })
  expect(recaps.mutateRecap).toHaveBeenCalledOnce()
  expect(sessionClient.authenticatedJson).toHaveBeenCalledTimes(2)
  const calls = vi.mocked(sessionClient.authenticatedJson).mock.calls
  expect(calls[1][0]).toBe(calls[0][0])
})

it('keeps a published recap published and never calls the status endpoint during upload', async () => {
  vi.mocked(recaps.fetchRecap).mockResolvedValue({ ...record, status: 'PUBLISHED' })
  vi.mocked(recaps.mutateRecap).mockResolvedValue({ ...record, status: 'PUBLISHED', version: 2 })
  vi.mocked(sessionClient.authenticatedJson).mockResolvedValue({ ...uploaded, status: 'PUBLISHED' })
  editor()
  const picker = await input()
  fireEvent.change(screen.getByLabelText(`${i18n.t('recaps.title')} · EN`), {
    target: { value: 'Edited published title' },
  })
  select(picker)
  await screen.findByAltText('Synthetic uploaded photo')
  expect(screen.getByRole('button', { name: i18n.t('recaps.unpublish') })).toBeEnabled()
  expect(recaps.mutateRecap).toHaveBeenCalledOnce()
  expect(recaps.mutateRecap).toHaveBeenCalledWith(
    `/${record.id}`,
    'PUT',
    expect.not.objectContaining({ status: expect.anything() }),
  )
  expect(sessionClient.authenticatedJson).toHaveBeenCalledOnce()
  expect(vi.mocked(sessionClient.authenticatedJson).mock.calls[0][0]).toContain(
    `/${record.id}/photos?`,
  )
})

it('rejects a drop exceeding the photo limit without an API request', async () => {
  vi.mocked(recaps.fetchRecap).mockResolvedValue({
    ...record,
    photos: Array.from({ length: 12 }, (_, index) => ({
      ...uploaded.photos[0],
      id: `22222222-2222-4222-8222-${String(index).padStart(12, '0')}`,
      sort_order: index,
    })),
  })
  editor()
  const picker = await input()
  expect(picker).toBeDisabled()
  fireEvent.drop(picker.closest('div')!, { dataTransfer: { files: [image()] } })
  expect(await screen.findByRole('alert')).toHaveTextContent(i18n.t('recaps.uploadInvalid'))
  expect(sessionClient.authenticatedJson).not.toHaveBeenCalled()
})

it('locks uploads during processing and reloads saved photos on a fresh editor', async () => {
  let complete!: (value: recaps.Recap) => void
  vi.mocked(sessionClient.authenticatedJson).mockReturnValue(
    new Promise((resolve) => {
      complete = resolve
    }),
  )
  const view = editor()
  const picker = await input()
  select(picker)
  await waitFor(() => expect(picker).toBeDisabled())
  expect(await screen.findByText(i18n.t('recaps.uploading'))).toBeVisible()
  fireEvent.drop(picker.closest('div')!, { dataTransfer: { files: [image()] } })
  expect(sessionClient.authenticatedJson).toHaveBeenCalledOnce()
  complete(uploaded)
  await screen.findByAltText('Synthetic uploaded photo')
  view.unmount()
  vi.mocked(recaps.fetchRecap).mockResolvedValue(uploaded)
  editor()
  expect(await screen.findByAltText('Synthetic uploaded photo')).toBeVisible()
  expect(screen.getByLabelText(`${i18n.t('recaps.alt')} · EN · 1`)).toHaveValue('Synthetic photo')
})

it('uploads selected files sequentially using each returned version', async () => {
  let completeFirst!: (value: recaps.Recap) => void
  vi.mocked(sessionClient.authenticatedJson)
    .mockReturnValueOnce(
      new Promise((resolve) => {
        completeFirst = resolve
      }),
    )
    .mockResolvedValueOnce({ ...uploaded, version: 4 })
  editor()
  fireEvent.change(await input(), { target: { files: [image(), image()] } })
  await waitFor(() => expect(sessionClient.authenticatedJson).toHaveBeenCalledOnce())
  expect(
    vi.mocked(sessionClient.authenticatedJson).mock.calls[0][1]?.formData?.get('version'),
  ).toBe('1')
  completeFirst(uploaded)
  await waitFor(() => expect(sessionClient.authenticatedJson).toHaveBeenCalledTimes(2))
  expect(
    vi.mocked(sessionClient.authenticatedJson).mock.calls[1][1]?.formData?.get('version'),
  ).toBe('3')
  expect(await screen.findByText(i18n.t('recaps.uploadDone'))).toBeVisible()
})
