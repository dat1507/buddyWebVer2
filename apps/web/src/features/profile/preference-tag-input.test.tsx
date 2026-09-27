import { useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { PreferenceTagMessages } from '@/features/profile/preference-tag-input'
import { PreferenceTagInput } from '@/features/profile/preference-tag-input'

const messages: PreferenceTagMessages = {
  inputLabel: 'Add value',
  placeholder: 'Custom value',
  add: 'Add custom value',
  customBadge: 'Custom',
  remove: (label) => `Remove ${label}`,
  invalid: 'Invalid value',
  duplicate: 'Duplicate value',
  predefinedCollision: 'Matches predefined value',
  limitReached: 'Limit reached',
  characterCount: (count, maximum) => `${count} of ${maximum} input characters`,
}

function Harness({ collisionLabels = [] }: { collisionLabels?: string[] }) {
  const [values, setValues] = useState<{ label: string }[]>([])
  return (
    <PreferenceTagInput
      values={values}
      collisionLabels={collisionLabels}
      selectedCount={values.length}
      maximum={3}
      messages={messages}
      onAdd={(label) => setValues((current) => [...current, { label }])}
      onRemove={(index) =>
        setValues((current) => current.filter((_, itemIndex) => itemIndex !== index))
      }
    />
  )
}

describe('PREF-004 shared custom preference tag input', () => {
  afterEach(cleanup)

  it('supports Enter, exposes an accessible remove action and restores input focus', () => {
    render(<Harness />)
    const input = screen.getByLabelText('Add value')

    fireEvent.change(input, { target: { value: '  Formula   1  ' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(screen.getByText('Formula 1')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Remove Formula 1' })).toBeVisible()
    expect(input).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Remove Formula 1' }))
    expect(screen.queryByText('Formula 1')).not.toBeInTheDocument()
    expect(input).toHaveFocus()
  })

  it('announces predefined collisions, Unicode-casefold duplicates and unsafe input', () => {
    render(<Harness collisionLabels={['Photography']} />)
    const input = screen.getByLabelText('Add value')

    fireEvent.change(input, { target: { value: ' Ｐｈｏｔｏｇｒａｐｈｙ ' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(screen.getByRole('alert')).toHaveTextContent('Matches predefined value')
    expect(input).toHaveAttribute('aria-invalid', 'true')

    fireEvent.change(input, { target: { value: 'Straße' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    fireEvent.change(input, { target: { value: 'STRASSE' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(screen.getByRole('alert')).toHaveTextContent('Duplicate value')
    expect(screen.getAllByText('Straße')).toHaveLength(1)

    fireEvent.change(input, { target: { value: 'unsafe\u200bvalue' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid value')
  })

  it('enforces the 255-character input boundary by Unicode code point', () => {
    render(<Harness />)
    const input = screen.getByLabelText('Add value')

    fireEvent.change(input, { target: { value: '😀'.repeat(256) } })

    expect(input).toHaveValue('😀'.repeat(255))
    expect(screen.getByText('255 of 255 input characters')).toBeVisible()
  })
})
