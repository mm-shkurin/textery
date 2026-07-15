// HTTP client for the registration API (POST create pending account).
// Base URL defaults to '' so requests go through the Vite dev proxy (/api → backend).
const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface RegisterResult {
  email: string
}

export interface RegisterApiError {
  errorCode: string
  message: string
}

export async function register(email: string, password: string): Promise<RegisterResult> {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const error: RegisterApiError = {
      errorCode: body.error_code ?? 'UNKNOWN_ERROR',
      message: body.message ?? 'Не удалось зарегистрироваться',
    }
    throw error
  }
  return res.json()
}
