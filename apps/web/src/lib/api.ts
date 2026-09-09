const apiBaseUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')

class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function getJson(path: string, signal?: AbortSignal): Promise<unknown> {
  if (!apiBaseUrl) {
    throw new Error('VITE_API_URL is not configured')
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!response.ok) {
    throw new ApiError(response.status, `API request failed with status ${response.status}`)
  }

  return response.json() as Promise<unknown>
}

export { ApiError, getJson }
