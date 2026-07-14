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
