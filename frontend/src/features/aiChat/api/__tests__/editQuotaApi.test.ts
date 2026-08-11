import { afterEach, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest'
import { loadEditQuota, type EditQuotaState } from '../editQuotaApi'
import { SessionExpiredError } from '../../../auth/api/authorizedRequest'
import { clearSession, saveSession } from '../../../auth/utils/authSession'
import { rejectionOf } from '../../../../test/rejectionOf'
import {
  expectErrorIdentity,
  okJson,
  QUOTA_URL,
  REFRESH_URL,
  SESSION_EXPIRED_MESSAGE,
  stubFetch,
  UNAUTHORIZED_RESPONSE,
} from './editorDocumentApiFixtures'

// THE CONTRACT ADDITION THIS FILE DEFINES, stated here because it does not exist yet and a
// parallel backend session has to honour it verbatim:
//
//   GET /api/v1/ai-edits/quota  ->  200 {"exhausted": bool, "resets_at": string | null}
//
// `endpoints.md` has seven endpoints and NONE of them reports quota state: `resets_at` lives only
// inside the 429 body of `POST /ai-edits`, i.e. only after the user has already typed an instruction
// and been refused. Scenario 0.2 requires the composer to be dead on arrival, so the same fact is
// needed BEFORE the first attempt. A gap recorded in `red-selenium` and `red-frontend`; this is
// where the path and the shape become concrete.
//
// NO `documentId` ANYWHERE — not in the signature and not in the path. The daily limit belongs
// to the account, and a `/documents/{id}/…` path would invite a per-document reading of a limit
// that is not per-document. `QUOTA_URL` (shared, beside its peer endpoint constants) is the path
// half of that claim; the `expectTypeOf` below is the signature half.
const FALLBACK = 'Не удалось загрузить лимит правок'

// Deliberately non-canonical: a +03:00 offset and no fractional seconds. Any `new Date(...)` /
// `toISOString()` on the mapping path rewrites it to '2026-08-10T21:00:00.000Z' and fails this file
// loudly — the point, because the Selenium layer asserts `data-resets-at` is byte-equal to what the
// API returned. Same constant as `DocumentEditorPage.overQuota.test.tsx`, so the layers cannot drift.
const RESETS_AT_WIRE = '2026-08-11T00:00:00+03:00'

// TDD RED (Story 19, Frontend Scenario 0.2). Verified failing 2026-08-11: every case fails on the
// stub's unconditional `Error: loadEditQuota is not implemented yet`. `describe.skip` rather than
// eight `it.skip`s: one function under test, one marker (the adapter-class convention this feature's
// `editorDocumentApi.test.ts` already uses). Unskipped in green-frontend-api.
describe.skip('editQuotaApi loadEditQuota', () => {
  // Setup, not subject: the read goes through `send` -> `authorizedRequest`, which throws
  // SessionExpiredError before fetch is reached when no token is stored.
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('reads the account-scoped quota and reports a quota that still has room', async () => {
    const fetchMock = stubFetch(okJson({ exhausted: false, resets_at: null }))

    // Whole-object, not per-field: it also fails if a wire field leaks through unrenamed
    // (`resets_at` alongside `resetsAt`), which a per-field check would not. `toStrictEqual` rather
    // than `toEqual` because `toEqual` treats an undefined-valued key as absent — a mapping that
    // forwarded `resets_at: undefined` alongside the rename would slip through it.
    await expect(loadEditQuota()).resolves.toStrictEqual({ exhausted: false, resetsAt: null })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    // `toBe`, not `toContain`: `toContain` also passes for '/api/v1/documents/x/ai-edits/quota',
    // which is the document-scoped path this whole module exists to refuse.
    expect(url).toBe(QUOTA_URL)
    // A read, and only a read, asserted as ONE CLOSED object rather than per-field checks: those
    // say nothing about keys they do not name, so a green adding `credentials: 'include'` or a
    // second header passes them all. `init` is exhaustively known — `performRequest` passes exactly
    // `{method, signal, headers, body}` (httpClient.ts:128-135) — so the whole object can be pinned.
    //
    // `method: 'GET'` and NOT an absence check: `performRequest` destructures
    // `const { method = 'GET' } = options` and passes `method` unconditionally, so `init` ALWAYS
    // carries the verb and an absence assertion could never go green. It also names the verb a
    // parallel backend session is bound to.
    //
    // `body: undefined` under `toStrictEqual` (which, unlike `toEqual`, does not treat an
    // undefined-valued key as absent) fails a green that smuggles a body onto this read — a client
    // that SPENDS a charge on every document open. The exact header set catches it a second way:
    // `performRequest` adds `Content-Type` the moment a body exists, so these headers cannot survive.
    //
    // `expect.any(AbortSignal)` is the one unavoidable matcher — the client injects a per-request
    // timeout signal no test can name a value for. Bounded by type, not an `expect.anything()` hole.
    expect(init).toStrictEqual({
      method: 'GET',
      signal: expect.any(AbortSignal),
      headers: { Authorization: 'Bearer access-1' },
      body: undefined,
    })
    // ZERO PARAMETERS, enforced rather than narrated. Every call site in this file passes no
    // argument, so a green that shipped `loadEditQuota(documentId?: string)` and appended it to the
    // path when present would leave the parameter dormant here and pass. The component layer's
    // `toHaveBeenCalledExactlyOnceWith()` pins what the CALLER passes, not what the adapter
    // ACCEPTS; the account-scoped signature is this module's own claim, so it is pinned in this
    // module. Folded into this already-failing case rather than given its own `it`, which would be
    // a case that passes from birth and was never red.
    //
    // `expectTypeOf`, not `loadEditQuota.length`: `.length` counts only the parameters BEFORE the
    // first defaulted or rest one, so `loadEditQuota(documentId = '')` and `loadEditQuota(...args)`
    // both report 0 and sail past an arity check. `toEqualTypeOf` is exact in both directions — a
    // signature that merely ACCEPTS zero arguments (`(documentId?: string) => …`, assignable to
    // `() => …`) fails it too. Verified: adding `documentId?: string` makes `tsc -b` fail here. It
    // is a compile-time gate, so unlike the rest of this file it is live while the describe skips.
    expectTypeOf(loadEditQuota).toEqualTypeOf<() => Promise<EditQuotaState>>()
  })

  // The scenario's Given, and the case the whole cross-layer byte-equality rests on.
  it('renames resets_at to resetsAt and carries the wire instant verbatim', async () => {
    stubFetch(okJson({ exhausted: true, resets_at: RESETS_AT_WIRE }))

    const quota = await loadEditQuota()

    expect(quota).toStrictEqual({ exhausted: true, resetsAt: RESETS_AT_WIRE })
    // The byte-equality above is only worth anything if RESETS_AT_WIRE is genuinely non-canonical,
    // and THAT was a property of a hand-written string that nothing enforced — a well-meaning
    // tidy-up to '2026-08-10T21:00:00.000Z' would leave every assertion in this file green while
    // silently deleting the round-trip trap they exist to spring. So the trap is asserted: a
    // `Date` round trip must CHANGE this constant. Replaces a `quota.exhausted && quota.resetsAt`
    // conjunction that re-stated the literal a third time and computed its actual through a
    // boolean branch.
    expect(new Date(RESETS_AT_WIRE).toISOString()).not.toBe(RESETS_AT_WIRE)
  })

  // The union's forbidden value, from the wire side. `{exhausted: true, resets_at: null}` is an
  // exhausted quota that cannot say when it lifts — the reset hint would render
  // `data-resets-at="null"` and the countdown would have nothing to count to. TypeScript makes it
  // unrepresentable in the RESULT; only this case stops the mapping from casting its way there
  // when the SERVER sends it. Refused as a load failure, which the component already degrades to
  // "quota not yet known" rather than to a broken hint.
  it('refuses an exhausted quota whose reset instant is missing', async () => {
    stubFetch(okJson({ exhausted: true, resets_at: null }))

    const error = await rejectionOf(loadEditQuota())
    expectErrorIdentity(error, Error, 'Error', FALLBACK)
  })

  // The mirror, and not decoration: the union's within-quota arm types `resetsAt` as exactly
  // `null`, so a mapping that forwards the field unchanged produces a value that lies about its
  // own type. The whole-object comparison is what fails here.
  it('drops a reset instant sent alongside a quota that is not exhausted', async () => {
    stubFetch(okJson({ exhausted: false, resets_at: RESETS_AT_WIRE }))

    await expect(loadEditQuota()).resolves.toStrictEqual({ exhausted: false, resetsAt: null })
  })

  // The third wire-side union guard, and the one reached through the SUCCESS path where none of
  // the refusals above look. `performRequest` ends with `await res.json().catch(() => ({}))`
  // (httpClient.ts:154), so a 204, an empty 200, or an HTML page served with a 200 all arrive at
  // the mapping as `{}` — not as a throw. A green written as `exhausted: Boolean(body.exhausted)`
  // or `body.exhausted === true` then answers `{exhausted: false, resetsAt: null}`: "the quota has
  // room", from an endpoint that said nothing at all — and the composer goes live. That is exactly
  // the state Scenario 0.2 exists to prevent, so silence must refuse rather than default to room.
  it.each([
    ['an empty body', {}],
    ['a non-boolean exhausted', { exhausted: 'false', resets_at: null }],
  ])('refuses a 200 that does not state the quota: %s', async (_case, body) => {
    stubFetch(okJson(body))

    const error = await rejectionOf(loadEditQuota())
    expectErrorIdentity(error, Error, 'Error', FALLBACK)
  })

  // An expired session is not a statement about the quota — the quota may well have room — and
  // flattening it into the generic failure would tell a signed-out user their limit could not be
  // read instead of that they are signed out. Two 401s: the first triggers `authorizedRequest`'s
  // renew-and-replay, the second is the refresh call failing, which is the only path that reaches
  // the caller as SessionExpiredError.
  it('lets SessionExpiredError through instead of describing it as a load failure', async () => {
    const fetchMock = stubFetch(UNAUTHORIZED_RESPONSE, UNAUTHORIZED_RESPONSE)

    const error = await rejectionOf(loadEditQuota())
    expectErrorIdentity(error, SessionExpiredError, 'SessionExpiredError', SESSION_EXPIRED_MESSAGE)
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([QUOTA_URL, REFRESH_URL])
  })

  // Everything else keeps the describing `send` already does. Pinning `name` to 'Error' is
  // stronger than a bare `not.toBeInstanceOf`: it rules out SessionExpiredError,
  // DocumentNotFoundError and any other subclass a green might reach for — including a green
  // that opts this call into the `notFound` mapping, which would be wrong here (a 404 on the
  // quota endpoint means the endpoint is missing, not that a document is).
  it('keeps a 500 as a described generic failure', async () => {
    const fetchMock = stubFetch({
      ok: false,
      status: 500,
      json: async () => ({ error_code: 'INTERNAL_ERROR', message: 'Внутренняя ошибка' }),
    })

    const error = await rejectionOf(loadEditQuota())
    expectErrorIdentity(error, Error, 'Error', 'Внутренняя ошибка')
    // Not a session problem: no renew, no replay.
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([QUOTA_URL])
  })
})
