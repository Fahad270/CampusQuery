// Set VITE_API_URL to the deployed Flask URL (for example
// https://campusquery-api.onrender.com). In local development the backend is
// expected on port 5000. Never put an API key in the frontend environment.
const configuredBase = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')
export const API_BASE = configuredBase || (import.meta.env.DEV ? 'http://localhost:5000' : '')

export class ApiError extends Error {
  constructor(message, { status = 0, kind = 'network' } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.kind = kind
  }
}

async function readJson(response) {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

export async function getHealth() {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 8000)

  try {
    const response = await fetch(`${API_BASE}/api/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal
    })
    const data = await readJson(response)

    if (!data) {
      throw new ApiError('The backend returned an invalid health response.', {
        status: response.status,
        kind: 'server'
      })
    }

    return data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error.name === 'AbortError') {
      throw new ApiError('The backend did not respond in time.', { kind: 'timeout' })
    }
    throw new ApiError('Could not reach the CampusQuery backend.', { kind: 'network' })
  } finally {
    clearTimeout(timer)
  }
}

export async function askQuestion(question) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 90000)

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ question }),
      signal: controller.signal
    })
    const data = await readJson(response)

    if (!response.ok) {
      throw new ApiError(
        data?.error || 'The assistant could not answer that question. Please try again.',
        { status: response.status, kind: response.status >= 500 ? 'server' : 'request' }
      )
    }

    if (!data || typeof data.answer !== 'string') {
      throw new ApiError('The backend returned an invalid answer.', { kind: 'server' })
    }

    return data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error.name === 'AbortError') {
      throw new ApiError('The answer took too long. Please try again.', { kind: 'timeout' })
    }
    throw new ApiError('Could not reach the CampusQuery backend.', { kind: 'network' })
  } finally {
    clearTimeout(timer)
  }
}
