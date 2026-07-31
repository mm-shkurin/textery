// Test support for `documentApi.transientFailureShape.test.ts` — the fixture and the assertion
// vocabulary for the H9.4 seam between what `saveDocument` REJECTS WITH and what the autosave
// retry policy can CLASSIFY. Extracted so both describes assert through ONE named vocabulary
// rather than one of them hand-rolling a weaker inline variant.
import { expect } from 'vitest'
import { RequestTimeoutError, isHttpError } from '../../../../shared/api/httpClient'
import { isTransientFailure, mayHaveLandedServerSide } from '../../hooks/autosaveRetryPolicy'
import { saveDocument, type SaveDocumentResult } from '../documentApi'
import { ACCESS_TOKEN, type FetchMock } from '../../../../shared/api/__tests__/originStubs'

// One definition of the request under test, shared by the call and by the assertion that reads
// the recorded fetch back — so a drifting literal cannot make the request assertion vacuous.
const SAVE_DOCUMENT_ID = 'doc-1'
const SAVE_CONTENT = '<p>ours</p>'
const SAVE_VERSION = 1

export function saveUnderTest(): Promise<SaveDocumentResult> {
  return saveDocument(SAVE_DOCUMENT_ID, SAVE_CONTENT, SAVE_VERSION)
}

// `.catch((e) => e)` also captures a RESOLVED value, so a `send` that stopped rejecting entirely
// would surface as `isHttpError(<save result>) === false` — a confusing failure that names the
// wrong defect. This says "expected a rejection" out loud instead.
export async function captureRejection(work: Promise<unknown>): Promise<unknown> {
  return work.then(
    (value) => {
      throw new Error(
        `expected saveDocument to reject, but it resolved with ${JSON.stringify(value)}`,
      )
    },
    (error: unknown) => error,
  )
}

const PENDING = Symbol('pending')

export async function isStillPending(work: Promise<unknown>): Promise<boolean> {
  return (await Promise.race([work, Promise.resolve(PENDING)])) === PENDING
}

// The EXACT rejection, not just `.status`. `httpClient` throws this object literal verbatim
// (httpClient.ts:141), so `toEqual` additionally fails on a body the transport invented and on a
// stray `retryAfterSeconds` — the two other fields of `HttpError` a partial assertion would miss.
function expectHttpRejection(
  rejection: unknown,
  status: number,
  body: Record<string, unknown> = {},
): void {
  expect(isHttpError(rejection)).toBe(true)
  expect(rejection).toEqual({ status, body })
}

// Both predicates in ONE diff, so a failure names which question got the wrong answer and at
// which status — four bare `toBe(true)` calls inside a helper all read `expected false to be true`.
function expectPolicyAnswers(rejection: unknown, transient: boolean, mayHaveLanded: boolean): void {
  expect({
    transient: isTransientFailure(rejection),
    mayHaveLanded: mayHaveLandedServerSide(rejection),
  }).toEqual({ transient, mayHaveLanded })
}

export function expectClassifiableAsTransient(
  rejection: unknown,
  status: number,
  body?: Record<string, unknown>,
): void {
  expectHttpRejection(rejection, status, body)
  expectPolicyAnswers(rejection, true, true)
}

// The one status where the two questions DIVERGE (autosaveRetryPolicy.ts:47-49). Without it
// `mayHaveLandedServerSide` could be `isTransientFailure` verbatim and this suite stays green,
// leaving the discriminating case of the H9.4 memory fix unpinned at this seam.
export function expectTransientButKnownNotToHaveLanded(rejection: unknown, status: number): void {
  expectHttpRejection(rejection, status)
  expectPolicyAnswers(rejection, true, false)
}

// The type-carrying half: `RequestTimeoutError` has no status, so it survives on IDENTITY.
// `name` and `message` are pinned alongside the instance check because the tell of the bug is a
// rejection whose MESSAGE looks right while its type is gone — asserting only the type would
// leave the mirror-image regression (right type, drifted text) unguarded, and `describeFailure`'s
// non-HttpError arm reads `.message`.
export function expectClassifiableAsTransientByIdentity(rejection: unknown): void {
  expect(rejection).toBeInstanceOf(RequestTimeoutError)
  expect({
    name: (rejection as Error).name,
    message: (rejection as Error).message,
  }).toEqual({ name: 'RequestTimeoutError', message: 'Request timed out' })
  expectPolicyAnswers(rejection, true, true)
}

// The request must actually have gone out, exactly once, as the PUT this scenario describes.
// Without this a `send` that rejected before ever calling fetch — or one that took `saveDocument`'s
// 409 refetch-and-retry branch (documentApi.ts:123-131) and fired three times — is green.
export function expectSingleSaveRequest(fetchMock: FetchMock): void {
  expect(fetchMock).toHaveBeenCalledTimes(1)
  const [url, init] = fetchMock.mock.calls[0]
  expect(url).toBe(`/api/v1/documents/${SAVE_DOCUMENT_ID}`)
  expect(init.method).toBe('PUT')
  // The session seeded in `beforeEach` is only load-bearing if the token is read back off the
  // wire: this is what pins that the REAL `authorizedRequest` layer ran, not a bypass of it.
  expect(init.headers).toEqual({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${ACCESS_TOKEN}`,
  })
  expect(JSON.parse(init.body as string)).toEqual({
    content: SAVE_CONTENT,
    version: SAVE_VERSION,
  })
}
