// What a `Response` MEANS: the error shape callers narrow on, and the two reads that turn a
// settled response into either a value or an HttpError. Nothing here builds a request or bounds
// one — see httpClient and requestTimeout for those.

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
  // Digits only, because `Number()` is far more generous than the contract: it reads '0x10' as 16
  // and '1e3' as 1000, so a malformed header would put the account-locked screen into a
  // seventeen-minute countdown the server never asked for. Anything that is not a plain integer
  // is treated as absent, which the field already means.
  if (!/^\d+$/.test(trimmed)) {
    return undefined
  }
  const seconds = Number(trimmed)
  return Number.isFinite(seconds) ? seconds : undefined
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

// A non-ok response, turned into the rejection every caller narrows on.
export async function toHttpError(res: Response): Promise<HttpError> {
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
  return error
}

// How to read a SUCCESSFUL body. 'json' is what every existing caller wants; 'blob' is for a
// binary stream (the document export download).
export type ResponseType = 'json' | 'blob'

// Reached only past the `res.ok` guard, so a 4xx/5xx never gets here — its error page was already
// turned into an HttpError, never a downloadable blob.
export async function readSuccessBody<T>(res: Response, responseType: ResponseType): Promise<T> {
  // Binary success: hand back the raw body untouched. No empty-body defence: `res.blob()` yields
  // an empty Blob rather than throwing, so there is no SyntaxError to swallow.
  if (responseType === 'blob') {
    return (await res.blob()) as T
  }
  // The success path needs the same defence the error path has. A 204, or a 200 with an empty
  // body, makes `res.json()` throw a bare SyntaxError — which `isHttpError` rejects, so it falls
  // through to the transport branch and the user is told the connection failed on a request that
  // succeeded. An empty successful body is "nothing to report", and `{}` says that.
  return (await res.json().catch(() => ({}))) as T
}
