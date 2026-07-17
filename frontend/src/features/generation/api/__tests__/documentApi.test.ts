import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createDocument, getDocument, saveDocument } from '../documentApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// Signing in is SETUP here, not subject: all three calls go through `authorizedRequest`, so
// without a session every one of them fails before fetch is reached. The refresh/replay
// machinery that setup enables is pinned in auth/api/__tests__/authorizedRequest.test.ts —
// these tests cover what this module owns: the wire mapping, the headers, and the error text.
describe('documentApi', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
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

  // Defect A (documents_create.yaml, DocumentResponse.version: "Optimistic-concurrency token;
  // required on subsequent PUT"). The old client parsed the response `as { document_id, status }`,
  // so version was discarded and ManualEditor fell back to `useState(1)` — a client-side guess
  // that 409s whenever the server's create version is anything but 1. 7 is deliberately not 1:
  // with 1 the guess and the answer are indistinguishable and this test would pass on the bug.
  it('createDocument returns the version the server assigned on create', async () => {
    stubCreateFetch(7)

    const result = await createDocument('doklad', 'key-1')

    expect(result).toEqual({ documentId: 'doc-1', status: 'draft', version: 7 })
  })

  // CORRECTION (measured by curl against the live backend 2026-07-17, superseding the spec and
  // this comment's earlier version): server-owned fields are IGNORED, not rejected. POST with
  // {"status":"completed","content":"<p>x</p>"} returns 201 with status="draft", content="" —
  // so the old client's `content: ''` was never the 422 the spec threatened, and NEW-1 as
  // originally written was a defect against a contract nobody implemented.
  //
  // The key-set assertion stays anyway, on a narrower claim: a request should say what it means,
  // and a field the server discards is a claim about ownership that is not the client's to make.
  it("createDocument sends document_type as the request body's only field", async () => {
    const fetchMock = stubCreateFetch()

    await createDocument('doklad', 'key-1')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/v1/documents')
    expect(init.method).toBe('POST')
    expect(Object.keys(JSON.parse(init.body)).sort()).toEqual(['document_type'])
  })

  // NEW-4, now SETTLED and pinned — this is the assertion test-review deliberately removed while
  // the question was open, restored because a measurement closed it. The backend kept Cyrillic
  // (docking-requirements.md asked for Latin and was not taken up), so the app's Latin
  // DocumentType is translated at this boundary. Measured, not read from a spec:
  //   {"document_type":"doklad"} -> 422 {"error_code":"INVALID_DOCUMENT_TYPE"}
  //   {"document_type":"доклад"} -> 201
  // Without this the editor creates nothing at all, and no other test in the suite would notice:
  // every one of them mocks fetch, so the wire value is only ever asserted here.
  it('createDocument translates the Latin DocumentType to the Cyrillic wire value', async () => {
    const fetchMock = stubCreateFetch()

    await createDocument('doklad', 'key-1')

    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body).document_type).toBe('доклад')
  })

  // Defect B: the key used to be minted inside createDocument, so every call sent a fresh one
  // and the spec's 200-replay branch was unreachable by construction. The caller owns it now —
  // stability across a logical create is pinned in documentApi.contract.test.ts. This pins the
  // header's presence and the spec's shape constraint (required, minLength 1, maxLength 128).
  // Deliberately NOT a UUID-shape assertion: the spec says "client-generated key", not "UUID",
  // and the old uuid regex here pinned the very per-call randomUUID() that caused the defect.
  it("createDocument sends the caller's Idempotency-Key and the session token", async () => {
    const fetchMock = stubCreateFetch()

    await createDocument('doklad', 'key-abc')

    const [, init] = fetchMock.mock.calls[0]
    expect(Object.keys(init.headers).sort()).toEqual([
      'Authorization',
      'Content-Type',
      'Idempotency-Key',
    ])
    expect(init.headers['Idempotency-Key']).toBe('key-abc')
    expect(init.headers['Content-Type']).toBe('application/json')
    // The whole point of the session: the backend cannot associate a document with a user it was
    // never told about. Without this, dropping the header breaks no other test here.
    expect(init.headers.Authorization).toBe('Bearer access-1')
  })

  // The returned `content` is the SANITIZED persisted form, not the string sent — measured
  // 2026-07-17: `<p>Привет</p><script>alert(1)</script><br />` came back as `<p>Привет</p><br>`.
  // The mock mirrors that (script stripped, `<br />` normalised) rather than echoing the input,
  // because echoing would let a client that drops `content` pass this test.
  it('saveDocument PUTs content and version, returns the sanitized content the server stored', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'draft', version: 2, content: '<p>Hello</p><br>' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await saveDocument('doc-1', '<p>Hello</p><script>x</script><br />', 1)

    expect(result).toEqual({ status: 'draft', version: 2, content: '<p>Hello</p><br>' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/v1/documents/doc-1')
    expect(init.method).toBe('PUT')
    expect(init.headers).toEqual({
      'Content-Type': 'application/json',
      Authorization: 'Bearer access-1',
    })
    expect(JSON.parse(init.body)).toEqual({
      content: '<p>Hello</p><script>x</script><br />',
      version: 1,
    })
  })

  // Deliberately 500, not 409: 409 is no longer a refusal to report but a protocol step the
  // client recovers from (see the conflict test below). Using it here would assert the message
  // of an error the user is never shown.
  it('saveDocument rejects with the server error message on a non-OK response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ message: 'Внутренняя ошибка сервера' }),
      }),
    )

    await expect(saveDocument('doc-1', '<p>Hello</p>', 1)).rejects.toThrow(
      'Внутренняя ошибка сервера',
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
    expect(url).toContain('/api/v1/documents/doc-1')
    expect(init.method).toBe('GET')
    // No body, so no Content-Type — the shared client sends it only when there IS JSON to
    // declare. Pinned because it is a deliberate choice, not an accident of the call.
    expect(init.headers).toEqual({ Authorization: 'Bearer access-1' })
  })

  it('getDocument rejects with server error detail on non-OK response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Документ не найден' }),
      }),
    )

    await expect(getDocument('doc-1')).rejects.toThrow('Документ не найден')
  })
})
