import { useEffect, useRef, useState } from 'react'

import { normalizeApiError } from '@/lib/api'
import type { ApiError } from '@/lib/api'

function useAuthSubmission() {
  const mounted = useRef(true)
  const busy = useRef(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [success, setSuccess] = useState(false)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const submit = async (work: () => Promise<unknown>, onSuccess?: () => void) => {
    if (busy.current) return
    busy.current = true
    setPending(true)
    setError(null)
    setSuccess(false)
    try {
      await work()
      if (mounted.current) {
        setSuccess(true)
        onSuccess?.()
      }
    } catch (failure) {
      if (mounted.current) setError(normalizeApiError(failure))
    } finally {
      busy.current = false
      if (mounted.current) setPending(false)
    }
  }
  const clearFeedback = () => {
    setError(null)
    setSuccess(false)
  }
  return { pending, error, success, submit, clearFeedback }
}

export { useAuthSubmission }
