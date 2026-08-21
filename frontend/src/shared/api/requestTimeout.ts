// The transport's own deadline, kept apart from request building and response decoding: nothing
// here knows what an HTTP response looks like, it only bounds how long any promise may run.

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
export function withTimeout<T>(
  work: (signal: AbortSignal) => Promise<T>,
  ms: number,
  caller?: AbortSignal,
): Promise<T> {
  const controller = new AbortController()
  // `AbortSignal.any` is not available everywhere this runs, so the two signals are joined by
  // hand: the caller's abort aborts ours, and the listener is removed when the work settles.
  const relay = () => controller.abort(caller?.reason)
  if (caller?.aborted) relay()
  else caller?.addEventListener('abort', relay, { once: true })

  let timer: ReturnType<typeof setTimeout>
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort()
      reject(new RequestTimeoutError())
    }, ms)
  })
  return Promise.race([work(controller.signal), timeout]).finally(() => {
    clearTimeout(timer)
    caller?.removeEventListener('abort', relay)
  })
}
