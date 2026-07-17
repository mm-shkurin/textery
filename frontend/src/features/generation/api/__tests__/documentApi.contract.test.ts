import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createDocument } from '../documentApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// Defect B (documents_create.yaml): the Idempotency-Key is `required: true` and "Replaying the
// same key returns the existing document (200) instead of creating a new one" — a documented
// response distinct from 201. createDocument used to call crypto.randomUUID() *inside* itself,
// so every call minted a fresh key and that 200 branch was unreachable by construction: the
// header was required, present, well-formed, and inert. main.tsx:7's StrictMode double-invokes
// effects and useDocumentInit's `cancelled` guard suppresses setState, not the fetch — two
// calls, two keys, two documents, on every dev mount.
//
// These tests pin the observable property, not a mechanism: retries of the SAME logical create
// send the SAME key; genuinely DIFFERENT creates send DIFFERENT keys.
//
// They are a matched pair, and this is the executed matrix, not a reasoned claim (the mutation
// notes this comment used to cite did not exist — test-review ran them instead):
//
//   key expression                       | retry-same | different
//   -------------------------------------|------------|----------
//   crypto.randomUUID()      (was)       | FAIL       | PASS
//   'fixed-key'              (constant)  | PASS       | FAIL
//   key ?? crypto.randomUUID()           | PASS       | PASS
//
// So neither test is redundant: each uniquely kills a trivial impl the other admits. Note what
// the matrix's top row meant while the defect was live: `different` passed on the DEFECTIVE
// code, because per-call randomUUID trivially differs. It never carried red signal against B —
// it guards against over-correcting to a constant key. Its green was never a green for B.
//
// The key is now a required parameter, so the `??` fallback row cannot be written at all: there
// is no in-function source to fall back TO. That is the point — an optional key was the escape
// hatch that let the keyless call site in useDocumentInit compile indefinitely while both these
// tests passed.
//
// Why the assertions are relational (`toBe`/`not.toBe`) rather than exact key values, per
// determinism-hierarchy's "truly opaque" category, which requires this justification
// written out: documents_create.yaml specifies the key ONLY relationally — "replaying the
// same key returns the existing document". The value is a "Client-generated key", opaque
// to the server by contract. Asserting `toEqual(['create-abc', 'create-xyz'])` would pin
// verbatim forwarding — a mechanism the spec does not mandate — and would fail a green
// that namespaces or derives the key (e.g. `doc-create:${key}`), which the contract
// permits. The relation is the specification; the value is not.
describe('documentApi create idempotency contract', () => {
  // Signing in is setup, not subject: createDocument goes through `authorizedRequest`, so
  // without a session it fails before fetch is reached.
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  function stubFetchOk(): ReturnType<typeof vi.fn> {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ document_id: 'doc-1', status: 'draft', content: '', version: 1 }),
    })
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  function sentKeys(fetchMock: ReturnType<typeof vi.fn>): string[] {
    return fetchMock.mock.calls.map(([, init]) => init.headers['Idempotency-Key'])
  }

  it('retrying the same logical create sends the same Idempotency-Key', async () => {
    const fetchMock = stubFetchOk()

    await createDocument('doklad', 'create-abc')
    await createDocument('doklad', 'create-abc')

    const [first, second] = sentKeys(fetchMock)
    expect(second).toBe(first)
  })

  // Live and passing, but NOT a red guard — see the matrix above: today it passes on the
  // defective per-call randomUUID. Kill power is against a constant-key green only.
  it('two different logical creates send different Idempotency-Keys', async () => {
    const fetchMock = stubFetchOk()

    await createDocument('doklad', 'create-abc')
    await createDocument('doklad', 'create-xyz')

    const [first, second] = sentKeys(fetchMock)
    expect(second).not.toBe(first)
  })
})
