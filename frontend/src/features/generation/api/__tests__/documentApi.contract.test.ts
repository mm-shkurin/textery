import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createDocument } from '../documentApi'

// Defect B (documents_create.yaml): the Idempotency-Key is `required: true` and
// "Replaying the same key returns the existing document (200) instead of creating a new
// one" — a documented response distinct from 201. documentApi.ts:16 calls
// crypto.randomUUID() *inside* createDocument, so every call mints a fresh key and that
// 200 branch is unreachable by construction: the header is required, present,
// well-formed, and inert. main.tsx:7's StrictMode double-invokes effects and
// useDocumentInit's `cancelled` guard suppresses setState, not the fetch — two calls,
// two keys, two documents, on every dev mount.
//
// These tests pin the observable property, not a mechanism: retries of the SAME logical
// create send the SAME key; genuinely DIFFERENT creates send DIFFERENT keys.
//
// They are a matched pair, and this is the executed matrix, not a reasoned claim (the
// mutation notes this comment used to cite did not exist — test-review ran them instead):
//
//   key expression                       | retry-same | different
//   -------------------------------------|------------|----------
//   crypto.randomUUID()      (today)     | FAIL       | PASS
//   'fixed-key'              (constant)  | PASS       | FAIL
//   key ?? crypto.randomUUID() (correct) | PASS       | PASS
//
// So neither test is redundant: each uniquely kills a trivial impl the other admits.
// NOTE what the matrix's top row means for the live test below: `different` passes TODAY,
// on the defective code, because per-call randomUUID trivially differs. It carries ZERO
// red signal against defect B — it is a guard on GREEN over-correcting to a constant key,
// not evidence that idempotency works. Its green is not a green for B.
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
  let uuidCounter = 0

  beforeEach(() => {
    uuidCounter = 0
    // Removes randomness from the failure message only; nothing here asserts that
    // randomUUID is the key's source, so this stays valid if green changes the source.
    vi.stubGlobal('crypto', { randomUUID: () => `uuid-${++uuidCounter}` })
  })

  afterEach(() => {
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

  // RED: createDocument accepts `idempotencyKey` (plumbing) but still mints a fresh
  // crypto.randomUUID() per call, so retries never replay — green-frontend-api-contract.
  it.skip('retrying the same logical create sends the same Idempotency-Key', async () => {
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
