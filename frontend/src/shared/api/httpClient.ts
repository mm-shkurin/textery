// Transport for every backend call: build the request, normalise a non-ok response into an
// HttpError, return the parsed body. It knows NOTHING about auth, and that is deliberate.
//
// Attaching the token here would make this module import the session, which would make the
// /auth/refresh client import a client that refreshes — a cycle, and worse, a refresh call
// that could recurse through its own 401 handling. So the auth concern lives exactly one layer
// up, in `shared/session/authorizedRequest.ts`, and the unauthenticated clients
// (login/register/verify/refresh) keep calling this module directly.
//
// Two concerns were lifted out of this file when it outgrew the 200-line cap, and they are the
// two that have nothing to do with building a request: `requestTimeout` bounds any promise, and
// `httpResponse` reads a settled `Response`. Both are re-exported here because this module is
// the transport's public face and every caller names it — moving the file should not move the
// import.
//
// Base URL defaults to '' so requests go through the Vite dev proxy (/api → backend).
import { readSuccessBody, toHttpError, type ResponseType } from './httpResponse'
import { REQUEST_TIMEOUT_MS, withTimeout } from './requestTimeout'

export { isHttpError, type HttpError } from './httpResponse'
export { REQUEST_TIMEOUT_MS, RequestTimeoutError } from './requestTimeout'

const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface RequestOptions {
  method?: string
  headers?: Record<string, string>
  body?: unknown
  // How to read a SUCCESSFUL body. Defaults to 'json' — every existing caller parses JSON. 'blob'
  // is for a binary stream (the document export download): the same res.ok / 401-renewal / timeout
  // guards apply, only the success read differs. It NEVER changes the error path — a non-ok
  // response is still parsed as JSON into an HttpError, so a 4xx/5xx error body is never streamed
  // out and downloaded as if it were the document.
  responseType?: ResponseType
  // The CALLER's cancellation — an unmounting component, a superseded search, a query the cache
  // has abandoned. Combined with the transport's own timeout signal rather than replacing it: a
  // request must stay bounded even when nobody cancels it, and must stop immediately when someone
  // does. Without this a fast re-navigation leaves responses in flight that resolve into
  // components that are gone.
  signal?: AbortSignal
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  // Every call — GET and mutating POST alike — is bounded: a hung POST is the one this scenario
  // exists for (login), and the bound is reject-only with no auto-retry, so bounding a POST is
  // safe against duplicates (see withTimeout).
  return withTimeout(
    (signal) => performRequest<T>(path, options, signal),
    REQUEST_TIMEOUT_MS,
    options.signal,
  )
}

// A BINARY body goes to the wire untouched. `PUT /auth/me/avatar` takes the image bytes
// themselves, not multipart and not a JSON envelope — and `JSON.stringify(blob)` is the string
// `"{}"`, which is a two-byte upload the server rejects as a corrupt image with no clue why.
// Its caller supplies the real Content-Type (`image/webp`); claiming `application/json` over
// image bytes is the same lie one layer up.
function isBinary(body: unknown): boolean {
  return body instanceof Blob || body instanceof ArrayBuffer || ArrayBuffer.isView(body)
}

function buildInit(options: RequestOptions, signal: AbortSignal): RequestInit {
  const { method = 'GET', headers = {}, body } = options
  const binary = isBinary(body)
  return {
    method,
    signal,
    // Content-Type is only truthful when there IS a body. Sending it on a GET tells the server
    // to expect JSON that never arrives.
    headers:
      body === undefined || binary ? headers : { 'Content-Type': 'application/json', ...headers },
    body: body === undefined ? undefined : binary ? (body as BodyInit) : JSON.stringify(body),
  }
}

async function performRequest<T>(
  path: string,
  options: RequestOptions,
  signal: AbortSignal,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, buildInit(options, signal))
  if (!res.ok) {
    throw await toHttpError(res)
  }
  return readSuccessBody<T>(res, options.responseType ?? 'json')
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body })
}
