// HTTP client for the auth resend-code endpoint.
// Base URL defaults to '' so requests go through the Vite dev proxy (/api → backend).
const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface ResendCodeResult {
  code: string
}

export async function resendCode(email: string): Promise<ResendCodeResult> {
  const res = await fetch(`${API_BASE}/api/v1/auth/resend-code`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  })
  if (!res.ok) {
    throw new Error(`Не удалось отправить код повторно (HTTP ${res.status})`)
  }
  return res.json()
}
