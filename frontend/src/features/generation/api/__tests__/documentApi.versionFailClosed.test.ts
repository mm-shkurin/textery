import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createDocument, getDocument, saveDocument, INVALID_VERSION_MESSAGE } from '../documentApi'
import { clearSession, saveSession } from '../../../../shared/session/authSession'

// Scenario H9.5 (08_Editor_Extension_Hazard_Tests.md §9.5): a version that is missing or
// unparseable must be REJECTED at the parse boundary, never a silent overwrite. Every feeder of a
// PUT's version — createDocument (seeds it), getDocument (the load and the 409 refetch), and the
// PUT response itself — goes through `send<DocumentWire>`, which casts the JSON blindly. A response
// whose `version` is absent (undefined), null, or unparseable ("abc"/NaN) would flow into the
// caller's version state and be PUT on the next autosave: the optimistic-concurrency token gone,
// the write no longer guarded by the version it claims — exactly the silent overwrite forbidden.
//
// FAIL-CLOSED CONTRACT: each of createDocument / getDocument / saveDocument must REJECT with an
// Error whose message is exactly INVALID_VERSION_MESSAGE (imported from production, one definition,
// no drifting inline copy) — not resolve with a garbage version, and not reject with the generic
// network fallback. The green guard is a finite-version check at the documentApi parse boundary.
type Settled = { rejected: false; value: unknown } | { rejected: true; error: unknown }

// Capture the settlement instead of `.rejects.toThrow()` (which allows ANY thrown value and any
// message): assert it REJECTED (an Error, not a resolved garbage result) AND that the message is
// exactly the fail-closed contract — pinning it apart from the network fallback.
async function settle(promise: Promise<unknown>): Promise<Settled> {
  return promise.then(
    (value) => ({ rejected: false as const, value }),
    (error: unknown) => ({ rejected: true as const, error }),
  )
}

function expectFailedClosed(settled: Settled): void {
  expect(settled.rejected).toBe(true)
  const error = (settled as { rejected: true; error: unknown }).error
  expect(error).toBeInstanceOf(Error)
  expect((error as Error).message).toBe(INVALID_VERSION_MESSAGE)
}

function okJson(
  status: number,
  body: Record<string, unknown>,
): { ok: true; status: number; json: () => Promise<Record<string, unknown>> } {
  return { ok: true, status, json: async () => body }
}

// Each bad shape is its own case so none is silently skipped when an earlier assertion fails: with
// no usable concurrency token anything returned is a guess the next autosave PUTs. Fail closed for
// every non-finite shape, with the SAME exact message. `NaN` cannot arrive over a real
// `response.json()` and is redundant with "abc" under Number.isFinite, but it is kept: it is a
// legitimate non-finite shape the one guard already covers, and pinning it documents the contract.
const badVersionShapes: ReadonlyArray<readonly [label: string, version: unknown]> = [
  ['version key absent (undefined)', undefined],
  ['version is null', null],
  ['version is an unparseable string', 'abc'],
  ['version is NaN', NaN],
]

function bodyWithVersion(base: Record<string, unknown>, version: unknown): Record<string, unknown> {
  const body = { ...base }
  if (version !== undefined) {
    body.version = version
  }
  return body
}

describe('documentApi version fail-closed (H9.5)', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  // createDocument seeds the version the FIRST autosave PUTs — the parse boundary where garbage
  // originates. A non-finite create version must reject, not return a token an autosave would send.
  for (const [label, version] of badVersionShapes) {
    it(`createDocument fails closed when ${label}`, async () => {
      const body = bodyWithVersion({ document_id: 'doc-1', status: 'draft', content: '' }, version)
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(okJson(201, body)))

      expectFailedClosed(await settle(createDocument('doklad', 'key-1')))
    })
  }

  // getDocument produces the version LATER autosaves send (the initial load, and the 409 refetch).
  // NaN is dropped here: it cannot survive real JSON, and the three reachable shapes prove the guard.
  for (const [label, version] of badVersionShapes.slice(0, 3)) {
    it(`getDocument fails closed when ${label}`, async () => {
      const body = bodyWithVersion(
        { document_id: 'doc-1', status: 'draft', content: '<p>x</p>' },
        version,
      )
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(okJson(200, body)))

      expectFailedClosed(await settle(getDocument('doc-1')))
    })
  }

  // The dangerous path: PUT 409s, saveDocument refetches, the refetch returns a garbage version.
  // Without the guard that token is re-PUT — the silent overwrite. The guard on getDocument makes
  // the refetch reject BEFORE the retry PUT, so the second PUT never fires with a bad token.
  it('saveDocument fails closed and never re-PUTs when the 409 refetch returns a garbage version', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({ error_code: 'VERSION_CONFLICT', message: 'conflict' }),
      })
      .mockResolvedValueOnce(
        okJson(200, {
          document_id: 'doc-1',
          status: 'draft',
          content: '<p>theirs</p>',
          version: 'abc',
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    expectFailedClosed(await settle(saveDocument('doc-1', '<p>ours</p>', 1)))
    // Exactly two calls: the original PUT (409) and the refetch GET. The retry PUT that would carry
    // the garbage token must never fire — asserting the count is how we prove the garbage was not sent.
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
