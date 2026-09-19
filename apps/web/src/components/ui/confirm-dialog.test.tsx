import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ConfirmDialog } from '@/components/ui/confirm-dialog'

const labels = {
  title: 'Delete event?',
  description: 'This action permanently removes the event.',
  confirmLabel: 'Delete event',
  cancelLabel: 'Keep event',
}

function DialogHarness({ onConfirm = () => undefined }: { onConfirm?: () => void }) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Open confirmation
      </button>
      <ConfirmDialog
        {...labels}
        open={open}
        onOpenChange={setOpen}
        onConfirm={onConfirm}
        destructive
      />
    </>
  )
}

describe('ADMIN-005 reusable ConfirmDialog', () => {
  it('portals an accessible modal, isolates background content, and focuses the safe action', () => {
    render(<DialogHarness />)

    const trigger = screen.getByRole('button', { name: 'Open confirmation' })
    const appContainer = trigger.parentElement
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()

    fireEvent.click(trigger)

    const dialog = screen.getByRole('alertdialog', { name: labels.title })
    expect(dialog).toHaveAccessibleDescription(labels.description)
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-busy', 'false')
    expect(screen.getByRole('button', { name: labels.cancelLabel })).toHaveFocus()
    expect(document.body).toHaveStyle({ overflow: 'hidden' })
    expect(appContainer).toHaveAttribute('aria-hidden', 'true')
    expect(appContainer).toHaveAttribute('inert')
  })

  it('cancels from Escape or the backdrop, restores focus, and ignores dialog clicks', () => {
    render(<DialogHarness />)
    const trigger = screen.getByRole('button', { name: 'Open confirmation' })
    trigger.focus()
    fireEvent.click(trigger)

    fireEvent.click(screen.getByRole('alertdialog'))
    expect(screen.getByRole('alertdialog')).toBeVisible()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
    expect(trigger.parentElement).not.toHaveAttribute('aria-hidden')
    expect(document.body).not.toHaveStyle({ overflow: 'hidden' })

    fireEvent.click(trigger)
    fireEvent.click(screen.getByTestId('confirm-dialog-backdrop'))
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  })

  it('traps forward and backward keyboard focus inside the dialog', () => {
    render(<DialogHarness />)
    fireEvent.click(screen.getByRole('button', { name: 'Open confirmation' }))
    const cancel = screen.getByRole('button', { name: labels.cancelLabel })
    const confirm = screen.getByRole('button', { name: labels.confirmLabel })

    expect(cancel).toHaveFocus()
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
    expect(confirm).toHaveFocus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(cancel).toHaveFocus()
  })

  it('runs the caller confirmation without implicitly closing controlled state', () => {
    const onConfirm = vi.fn()
    render(<DialogHarness onConfirm={onConfirm} />)
    fireEvent.click(screen.getByRole('button', { name: 'Open confirmation' }))

    fireEvent.click(screen.getByRole('button', { name: labels.confirmLabel }))

    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('alertdialog')).toBeVisible()
  })

  it('blocks dismissal and duplicate actions while pending, with caller-owned status copy', () => {
    const onOpenChange = vi.fn()
    const onConfirm = vi.fn()
    render(
      <ConfirmDialog
        {...labels}
        open
        onOpenChange={onOpenChange}
        onConfirm={onConfirm}
        isPending
        pendingLabel="Deleting event"
      />,
    )

    const dialog = screen.getByRole('alertdialog')
    const cancel = screen.getByRole('button', { name: labels.cancelLabel })
    const confirm = screen.getByRole('button', { name: 'Deleting event' })
    expect(dialog).toHaveAttribute('aria-busy', 'true')
    expect(cancel).toBeDisabled()
    expect(confirm).toBeDisabled()
    expect(confirm).toHaveAttribute('aria-busy', 'true')

    fireEvent.keyDown(document, { key: 'Escape' })
    fireEvent.click(screen.getByTestId('confirm-dialog-backdrop'))
    fireEvent.click(cancel)
    fireEvent.click(confirm)
    expect(onOpenChange).not.toHaveBeenCalled()
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('keeps focus in the modal when the active confirmation becomes disabled', () => {
    const { rerender } = render(
      <ConfirmDialog {...labels} open onOpenChange={() => undefined} onConfirm={() => undefined} />,
    )
    const confirm = screen.getByRole('button', { name: labels.confirmLabel })
    confirm.focus()
    expect(confirm).toHaveFocus()

    rerender(
      <ConfirmDialog
        {...labels}
        open
        onOpenChange={() => undefined}
        onConfirm={() => undefined}
        isPending
        pendingLabel="Deleting event"
      />,
    )

    expect(screen.getByRole('alertdialog')).toHaveFocus()
  })

  it('supports dependency blocking, safe structured copy, and an announced caller error', () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmDialog
        open
        onOpenChange={() => undefined}
        onConfirm={onConfirm}
        title="Cannot delete event"
        description={
          <>
            Remove <strong>3 registrations</strong> first.
          </>
        }
        confirmLabel="Delete event"
        cancelLabel="Close"
        confirmDisabled
        error="The event changed. Refresh and try again."
        destructive
      />,
    )

    const dialog = screen.getByRole('alertdialog', { name: 'Cannot delete event' })
    expect(dialog).toHaveAccessibleDescription(
      'Remove 3 registrations first. The event changed. Refresh and try again.',
    )
    expect(screen.getByRole('alert')).toHaveTextContent('The event changed. Refresh and try again.')
    const confirm = screen.getByRole('button', { name: 'Delete event' })
    expect(confirm).toBeDisabled()
    fireEvent.click(confirm)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('restores pre-existing body and sibling accessibility state when unmounted', () => {
    document.body.style.overflow = 'clip'
    const sibling = document.createElement('div')
    sibling.setAttribute('aria-hidden', 'false')
    sibling.setAttribute('inert', 'persist')
    document.body.append(sibling)

    const { unmount } = render(
      <ConfirmDialog {...labels} open onOpenChange={() => undefined} onConfirm={() => undefined} />,
    )
    expect(sibling).toHaveAttribute('aria-hidden', 'true')
    expect(sibling).toHaveAttribute('inert', '')

    unmount()
    expect(document.body).toHaveStyle({ overflow: 'clip' })
    expect(sibling).toHaveAttribute('aria-hidden', 'false')
    expect(sibling).toHaveAttribute('inert', 'persist')
    sibling.remove()
    document.body.style.overflow = ''
  })
})
