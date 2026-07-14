// HTTP client for the auth resend-code endpoint.
// Base URL defaults to '' so requests go through the Vite dev proxy (/api → backend).
const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface ResendCodeResult {
  code: string
}

export async function resendCode(email: string): Promise<ResendCodeResult> {
  throw new Error('Not implemented')
}
