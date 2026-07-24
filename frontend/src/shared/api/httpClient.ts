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

// Client-side timeout for a single request. Its job is to stop a HUNG request (a proxy that
// black-holes the POST, a dropped SYN) from spinning forever with no catch and no finally ever
// running — the fetch promise would otherwise stay pending and the caller's submitting state
// never resets. See LoginForm.indefiniteSpinner.test.tsx.
//
// The bound is deliberately GENEROUS, not tight: this transport is SHARED by every flow —
// register/verify/refresh AND a real document generation, which the backend can take ~20s+ to
// answer. A short bound would abort a slow-but-valid generation and show a false connection
// error. So the floor is the slowest legitimate flow's budget (pinned ≥ 20s by
// httpClient.timeout.test.ts), and this value clears it with margin while still capping a
// genuine hang well inside a human's patience.
export const REQUEST_TIMEOUT_MS = 25_000

// A timeout is a TRANSPORT failure, not an HTTP response: it carries no `status` and no `body`,
// so `isHttpError` is false and `toAuthApiError` rethrows it untouched — which is exactly what
// routes it to the form's `login-network-error` / retry-capable state (the `!errorCode`
// transport branch), never to a field-level validation message.
export class RequestTimeoutError extends Error {
  constructor() {
    super('Request timed out')
    this.name = 'RequestTimeoutError'
  }
}

// Race the real work against a timer that REJECTS on its own — independently of whether the
// transport observes any abort signal. A signal-only fix (fetch({signal})) is not enough: a
// black-holed connection may never honour the abort, leaving the fetch pending forever; the
// timer rejecting is what converts the hang into a rejection regardless.
//
// This does NOT abort the underlying request, and DELIBERATELY does not retry it. A client that
// stops waiting has not undone a mutating POST the server may already be processing — silently
// replaying it would risk a DUPLICATE registration/generation. So a timeout surfaces as an
// error with a retry AFFORDANCE (the form re-enables its submit button); the actual retry is the
// user's explicit choice, never an automatic replay. Generation's POST additionally carries an
// Idempotency-Key, so even a user-driven retry collapses server-side rather than duplicating.
//
// The abort is belt to the timer's braces, and only that: it releases the socket and the pending
// response handling instead of leaving them to the garbage collector's mercy, which matters most
// under the 5s generation poll where abandoned connections would otherwise accumulate. It is NOT
// what makes the timeout work — a black-holed connection may never honour it — so the timer still
// rejects independently, and aborting changes nothing about the no-auto-retry reasoning above:
// giving up on a response never unsends the request.
function withTimeout<T>(work: (signal: AbortSignal) => Promise<T>, ms: number): Promise<T> {
  const controller = new AbortController()
  let timer: ReturnType<typeof setTimeout>
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort()
      reject(new RequestTimeoutError())
    }, ms)
  })
  return Promise.race([work(controller.signal), timeout]).finally(() => clearTimeout(timer))
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
  // Every call — GET and mutating POST alike — is bounded: a hung POST is the one this scenario
  // exists for (login), and the bound is reject-only with no auto-retry, so bounding a POST is
  // safe against duplicates (see withTimeout).
  return withTimeout((signal) => performRequest<T>(path, options, signal), REQUEST_TIMEOUT_MS)
}

async function performRequest<T>(
  path: string,
  options: RequestOptions,
  signal: AbortSignal,
): Promise<T> {
  const { method = 'GET', headers = {}, body } = options
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    signal,
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
