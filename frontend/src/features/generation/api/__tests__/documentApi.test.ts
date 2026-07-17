import { afterEach, describe, expect, it, vi } from 'vitest'
import { createDocument, getDocument, saveDocument } from '../documentApi'
import { API_BASE } from '../httpClient'

describe('documentApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // The 201 body every create test stubs. `version` is the only literal any of them varies
  // (defect A's test needs a value other than ManualEditor's useState(1) guess to prove the
  // server's is taken), so it is the only parameter.
  function stubCreateFetch(version = 1): ReturnType<typeof vi.fn> {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ document_id: 'doc-1', status: 'draft', content: '', version }),
    })
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  // Defect A (documents_create.yaml, DocumentResponse.version: "Optimistic-concurrency
  // token; required on subsequent PUT"). documentApi.ts:19 parses the response
  // `as { document_id, status }`, so version is discarded and ManualEditor.tsx:38 falls
  // back to `useState(1)` — a client-side guess that 409s if the server's create version
  // is anything but 1.
  // RED: documentApi.ts drops `version` on the create path — green-frontend-api-contract.
  it.skip('createDocument returns the version the server assigned on create', async () => {
    stubCreateFetch(7)

    const result = await createDocument('doklad')

    expect(result).toEqual({ documentId: 'doc-1', status: 'draft', version: 7 })
  })

  // Defect NEW-1 (documents_create.yaml, 422: "a request body containing a server-owned
  // field (status, id, content)"). documentApi.ts:22-25 sends `content: ''`, so every
  // create 422s against a spec-conformant backend. CreateDocumentRequest has exactly one
  // property, document_type — the key set, not just the absence of `content`, is the
  // contract, so a future server-owned field cannot be added without failing here.
  // RED: documentApi.ts still sends the server-owned `content` — green-frontend-api-contract.
  //
  // This test asserts the body's KEY SET and deliberately asserts NOTHING about
  // document_type's VALUE. That is not an oversight and not a loosening — the value is
  // undecided and out of this red's scope (defect NEW-4, below).
  //
  // NEW-4 — the client's document_type values are Latin, the spec's enum is Cyrillic.
  // documents_create.yaml: `enum: [доклад, эссе, сочинение, реферат]`; documentTypes.ts:1:
  // `type DocumentType = 'doklad' | 'essay' | 'sochinenie' | 'referat'`. So a create also
  // 422s on "Unsupported document_type" — a FOURTH defect, distinct from A/B/NEW-1. Which
  // side moves (client sends Cyrillic / client maps / spec adopts Latin) is a product +
  // contract decision needing /design-preview; the gaps section says to "check it in the
  // red, do not assume either way".
  //
  // An earlier draft asserted `body.document_type === 'doklad'`. test-review removed it on
  // executed evidence, not on reading: against a mutant that drops `content` AND sends the
  // spec-conformant Cyrillic `'доклад'`, that assertion fails —
  //   AssertionError: expected 'доклад' to be 'doklad'
  // i.e. it did not merely pin NEW-4's defect as correct, it would have actively BLOCKED
  // the correct fix, and forced green to either change a RED expected value (forbidden,
  // tdd-rules:26) or stop. It was also a pure input→output identity assertion on the
  // test's own argument (tdd-rules:18's trivial gate). The key-set claim this test exists
  // to make does not need it. When NEW-4 is decided, pin the wire value in its own test.
  it.skip('createDocument sends document_type as the request body\'s only field', async () => {
    const fetchMock = stubCreateFetch()

    await createDocument('doklad')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toEqual(`${API_BASE}/api/v1/documents`)
    expect(init.method).toBe('POST')
    const body = JSON.parse(init.body)
    expect(Object.keys(body).sort()).toEqual(['document_type'])
  })

  // The Idempotency-Key's *stability* is pinned in documentApi.contract.test.ts; this
  // only pins the header's presence and the spec's shape constraint (required: true,
  // minLength: 1, maxLength: 128). Deliberately NOT a UUID-shape assertion — the spec
  // says "client-generated key", not "UUID", and the old uuid regex here pinned the
  // per-call crypto.randomUUID() that makes the documented 200-replay branch unreachable.
  it('createDocument sends a Content-Type and a spec-shaped Idempotency-Key header', async () => {
    const fetchMock = stubCreateFetch()

    await createDocument('doklad')

    const [, init] = fetchMock.mock.calls[0]
    expect(Object.keys(init.headers).sort()).toEqual(['Content-Type', 'Idempotency-Key'])
    expect(init.headers['Content-Type']).toBe('application/json')
    const key = init.headers['Idempotency-Key']
    expect(typeof key).toBe('string')
    expect(key.length).toBeGreaterThanOrEqual(1)
    expect(key.length).toBeLessThanOrEqual(128)
  })

  it('saveDocument PUTs content and version, returns saved status + version', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'draft', version: 2 }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await saveDocument('doc-1', '<p>Hello</p>', 1)

    expect(result).toEqual({ status: 'draft', version: 2 })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toEqual(`${API_BASE}/api/v1/documents/doc-1`)
    expect(init.method).toBe('PUT')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(init.body)).toEqual({
      content: '<p>Hello</p>',
      version: 1,
    })
  })

  it('saveDocument rejects with server error detail on non-OK response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ detail: 'Версия документа устарела' }),
      })
    )

    await expect(saveDocument('doc-1', '<p>Hello</p>', 1)).rejects.toThrow(
      'Версия документа устарела'
    )
  })

  it('getDocument GETs the document and returns documentId, status, content, version', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        document_id: 'doc-1',
        status: 'draft',
        content: '<p>Saved</p>',
        version: 3,
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await getDocument('doc-1')

    expect(result).toEqual({
      documentId: 'doc-1',
      status: 'draft',
      content: '<p>Saved</p>',
      version: 3,
    })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toEqual(`${API_BASE}/api/v1/documents/doc-1`)
    expect(init.method).toBe('GET')
  })

  it('getDocument rejects with server error detail on non-OK response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Документ не найден' }),
      })
    )

    await expect(getDocument('doc-1')).rejects.toThrow('Документ не найден')
  })
})
