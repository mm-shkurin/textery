// Shared HTTP helpers for the generation feature's API clients.
export const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

export async function readErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    const detail = body?.detail ?? body?.message
    if (typeof detail === 'string' && detail.trim()) return detail
  } catch {
    // body isn't JSON or is empty — fall through to fallback
  }
  return `${fallback} (HTTP ${res.status})`
}

// Shared fetch → error-check → JSON-parse skeleton used by every generation-feature
// API client. Callers map the raw response body into their own typed result shape.
export async function request(
  url: string,
  options: RequestInit,
  errorFallback: string
): Promise<unknown> {
  const res = await fetch(url, options)
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, errorFallback))
  }
  return res.json()
}
