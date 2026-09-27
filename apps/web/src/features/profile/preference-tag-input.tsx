import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { Plus, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  MAX_CUSTOM_PREFERENCE_INPUT_LENGTH,
  preferenceComparisonKey,
  preparePreferenceIdentity,
} from '@/features/profile/preference-normalization'
import { cn } from '@/lib/utils'

const inputClassName =
  'h-11 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none transition placeholder:text-muted-foreground/70 hover:border-foreground/25 focus-visible:border-vgu-orange focus-visible:ring-2 focus-visible:ring-vgu-orange/25 disabled:cursor-not-allowed disabled:opacity-60'

interface CustomPreferenceValue {
  label: string
}

interface PreferenceTagMessages {
  inputLabel: string
  placeholder: string
  add: string
  customBadge: string
  remove: (label: string) => string
  invalid: string
  duplicate: string
  predefinedCollision: string
  limitReached: string
  characterCount: (count: number, maximum: number) => string
}

interface PreferenceTagInputProps<T extends CustomPreferenceValue> {
  values: readonly T[]
  collisionLabels: readonly string[]
  selectedCount: number
  maximum: number
  disabled?: boolean
  messages: PreferenceTagMessages
  inputAccessory?: ReactNode
  renderValueControl?: (value: T, index: number) => ReactNode
  onAdd: (label: string) => void
  onRemove: (index: number) => void
}

function PreferenceTagInput<T extends CustomPreferenceValue>({
  values,
  collisionLabels,
  selectedCount,
  maximum,
  disabled = false,
  messages,
  inputAccessory,
  renderValueControl,
  onAdd,
  onRemove,
}: PreferenceTagInputProps<T>) {
  const inputId = useId()
  const helpId = useId()
  const errorId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const atLimit = selectedCount >= maximum

  const addValue = () => {
    if (disabled) return
    if (atLimit) {
      setError(messages.limitReached)
      return
    }

    const identity = preparePreferenceIdentity(input)
    if (!identity) {
      setError(messages.invalid)
      return
    }

    const customKeys = new Set(values.map(({ label }) => preferenceComparisonKey(label)))
    if (customKeys.has(identity.comparisonKey)) {
      setError(messages.duplicate)
      return
    }

    const catalogKeys = new Set(collisionLabels.map(preferenceComparisonKey))
    if (catalogKeys.has(identity.comparisonKey)) {
      setError(messages.predefinedCollision)
      return
    }

    onAdd(identity.displayLabel)
    setInput('')
    setError(null)
    inputRef.current?.focus()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'Enter') return
    event.preventDefault()
    addValue()
  }

  return (
    <div className="space-y-3 rounded-xl border border-dashed border-border p-4">
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <div className="min-w-0 space-y-2">
          <label htmlFor={inputId} className="text-sm font-medium">
            {messages.inputLabel}
          </label>
          <input
            ref={inputRef}
            id={inputId}
            value={input}
            disabled={disabled || atLimit}
            className={inputClassName}
            placeholder={messages.placeholder}
            aria-describedby={`${helpId}${error ? ` ${errorId}` : ''}`}
            aria-invalid={Boolean(error)}
            onChange={(event) => {
              setInput(
                Array.from(event.target.value)
                  .slice(0, MAX_CUSTOM_PREFERENCE_INPUT_LENGTH)
                  .join(''),
              )
              setError(null)
            }}
            onKeyDown={handleKeyDown}
          />
          <p id={helpId} className="text-xs text-muted-foreground">
            {messages.characterCount(Array.from(input).length, MAX_CUSTOM_PREFERENCE_INPUT_LENGTH)}
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          {inputAccessory}
          <Button
            type="button"
            variant="outline"
            disabled={disabled || atLimit || !input.trim()}
            onClick={addValue}
          >
            <Plus aria-hidden="true" />
            {messages.add}
          </Button>
        </div>
      </div>

      {error ? (
        <p id={errorId} className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      {values.length > 0 ? (
        <ul className="flex flex-wrap gap-2">
          {values.map((value, index) => (
            <li
              key={preferenceComparisonKey(value.label) ?? value.label}
              className="flex min-w-0 max-w-full flex-wrap items-center gap-2 rounded-xl border border-vgu-orange/40 bg-vgu-orange/10 px-3 py-2"
            >
              <span className="rounded-full bg-vgu-orange/15 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-vgu-orange-dark dark:text-vgu-orange">
                {messages.customBadge}
              </span>
              <span className="min-w-0 break-words text-sm font-medium">{value.label}</span>
              {renderValueControl?.(value, index)}
              <button
                type="button"
                className={cn(
                  'ml-auto inline-flex size-8 shrink-0 items-center justify-center rounded-full text-muted-foreground transition hover:bg-background hover:text-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange',
                )}
                disabled={disabled}
                aria-label={messages.remove(value.label)}
                onClick={() => {
                  setError(null)
                  onRemove(index)
                  inputRef.current?.focus()
                }}
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

export { PreferenceTagInput }
export type { CustomPreferenceValue, PreferenceTagMessages }
