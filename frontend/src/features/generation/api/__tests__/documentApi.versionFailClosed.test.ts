import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createDocument } from '../documentApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// Scenario H9.5 (08_Editor_Extension_Hazard_Tests.md §9.5): an autosave whose version is missing
// or unparseable must be REJECTED, never a silent overwrite. The autosave PUT carries a version
// seeded from the create response and updated from every save/refetch response — `send<DocumentWire>`
// casts that JSON blindly, so a response whose `version` is absent (undefined), null, or unparseable
// ("abc"/NaN) flows straight into useDocumentSave's version state and is PUT on the next autosave.
// A PUT carrying `version: undefined`/NaN is exactly the silent overwrite the hazard forbids: the
// optimistic-concurrency token is gone, so the write is no longer guarded by the version it claims.
//
// This pins the parse boundary where the garbage ORIGINATES: createDocument must fail closed when
// the server's version is not a finite number, rather than returning a token the first autosave
// would send. The same guard belongs on getDocument and saveDocument (green), which produce the
// versions later autosaves send.
//
// FAIL-CLOSED CONTRACT (the spec this test defines): createDocument must REJECT with an Error whose
// message is exactly INVALID_VERSION_MESSAGE — not resolve with a garbage version, and not reject
// with the generic network fallback ('Не удалось создать документ'). green-frontend adds a
// finite-version guard at the parse boundary that throws exactly this message. Unskip in green.
const INVALID_VERSION_MESSAGE = 'Сервер вернул документ без корректной версии.'

describe('documentApi version fail-closed (H9.5)', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  function stubCreateResponse(body: Record<string, unknown>): void {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 201, json: async () => body }),
    )
  }

  // Each bad shape is its own case so none is silently skipped when an earlier assertion fails:
  // a create response with no usable concurrency token means anything returned is a guess the first
  // autosave PUTs. Fail closed for every non-finite shape, with the SAME exact message.
  const badVersionShapes: ReadonlyArray<readonly [label: string, version: unknown]> = [
    ['version key absent (undefined)', undefined],
    ['version is null', null],
    ['version is an unparseable string', 'abc'],
    ['version is NaN', NaN],
  ]

  // RED (H9.5): no guard rejects a non-finite version anywhere on the save path today —
  // createDocument returns the garbage version and the first autosave PUTs it. These stay skipped
  // until green adds the finite-version check at the parse boundary.
  for (const [label, version] of badVersionShapes) {
    it.skip(`createDocument fails closed when ${label}`, async () => {
      const body: Record<string, unknown> = { document_id: 'doc-1', status: 'draft', content: '' }
      if (version !== undefined) {
        body.version = version
      }
      stubCreateResponse(body)

      // Capture the settlement instead of `.rejects.toThrow()` (which allows ANY thrown value and
      // any message): assert it REJECTED (an Error, not a resolved garbage result) AND that the
      // message is exactly the fail-closed contract — pinning it apart from the network fallback.
      const settled = await createDocument('doklad', 'key-1').then(
        (value) => ({ rejected: false as const, value }),
        (error: unknown) => ({ rejected: true as const, error }),
      )

      expect(settled.rejected).toBe(true)
      const error = (settled as { rejected: true; error: unknown }).error
      expect(error).toBeInstanceOf(Error)
      expect((error as Error).message).toBe(INVALID_VERSION_MESSAGE)
    })
  }
})
