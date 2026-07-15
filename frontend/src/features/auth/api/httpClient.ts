// Shared JSON POST helper for the auth API clients.
// Base URL defaults to '' so requests go through the Vite dev proxy (/api → backend).
const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface HttpError {
  status: number
  body: Record<string, unknown>
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const parsedBody = await res.json().catch(() => ({}))
    const error: HttpError = { status: res.status, body: parsedBody }
    throw error
  }
  return res.json()
}
