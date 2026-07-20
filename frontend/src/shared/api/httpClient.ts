// Transport for every backend call: build the request, normalise a non-ok response into an
// HttpError, return the parsed body. It knows NOTHING about auth, and that is deliberate.
//
// Attaching the token here would make this module import the session, which would make the
// /auth/refresh client import a client that refreshes — a cycle, and worse, a refresh call
// that could recurse through its own 401 handling. So the auth concern lives exactly one layer
// up, in `features/auth/api/authorizedRequest.ts`, and the unauthenticated clients
// (login/register/verify/refresh) keep calling this module directly.
//
// Base URL defaults to '' so requests go through the Vite dev proxy (/api → backend).
const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface HttpError {
  status: number
  body: Record<string, unknown>
  // Present ONLY when the response carried a parseable `Retry-After` delta-seconds header (5.4
  // lockout / any 429). Absent otherwise — never NaN — so a reader can trust `typeof === 'number'`.
  retryAfterSeconds?: number
}

// Retry-After as delta-seconds → a finite non-negative integer, or undefined. RFC 9110 also allows
// an HTTP-date form; we deliberately do NOT support it (our backend sends seconds), and a date or
// any garbage yields undefined rather than NaN — the field is best-effort, absence is meaningful.
function parseRetryAfterSeconds(headers: Headers | undefined): number | undefined {
  const raw = headers?.get('Retry-After') ?? null
  if (raw === null) {
    return undefined
  }
  const trimmed = raw.trim()
  if (trimmed === '') {
    return undefined
  }
  const seconds = Number(trimmed)
  return Number.isFinite(seconds) && seconds >= 0 ? Math.floor(seconds) : undefined
}

export interface RequestOptions {
  method?: string
  headers?: Record<string, string>
  body?: unknown
}

// Rejections reach callers as `unknown`, and only SOME of them are HttpError: a transport
// failure rejects with a bodyless TypeError from fetch itself. Callers that read `.status` or
// `.body` must narrow first — reading them off a TypeError yields `undefined` and turns a
// network outage into a phantom "HTTP undefined".
export function isHttpError(error: unknown): error is HttpError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    typeof (error as { status: unknown }).status === 'number' &&
    'body' in error
  )
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', headers = {}, body } = options
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    // Content-Type is only truthful when there IS a body. Sending it on a GET tells the server
    // to expect JSON that never arrives.
    headers: body === undefined ? headers : { 'Content-Type': 'application/json', ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    // A non-JSON error page (a proxy's 502, an HTML 404) makes `res.json()` throw. Substituting
    // `{}` keeps the rejection an HttpError carrying the real status, so callers can still tell
    // 401 from 500 — which is the one fact the body was never going to give them.
    const parsedBody = await res.json().catch(() => ({}))
    const error: HttpError = { status: res.status, body: parsedBody }
    // Preserve the cooldown the 5.4 account-locked screen counts down. Header-driven: attached only
    // when a parseable value is present, on ANY non-ok response — not scoped to a specific code.
    const retryAfterSeconds = parseRetryAfterSeconds(res.headers)
    if (retryAfterSeconds !== undefined) {
      error.retryAfterSeconds = retryAfterSeconds
    }
    throw error
  }
  return res.json()
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body })
}
