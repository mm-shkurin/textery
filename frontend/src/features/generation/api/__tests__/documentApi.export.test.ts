import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { exportDocument } from '../documentApi'
import { clearSession, saveSession } from '../../../../shared/session/authSession'

// Scenario 2.1 — the export REQUEST contract only. exportDocument(documentId, format) must issue
// GET /api/v1/documents/{documentId}/export?format=<pdf|docx> (documents_export.yaml, owner-scoped,
// read-only), carry the session token, and hand back the binary body the server streamed. The
// browser download-trigger (anchor click / object URL) is scenario 5.1 and is NOT asserted here —
// this test stops at the HTTP request shape and the response passthrough.
//
// Signing in is SETUP, not subject: export is owner-scoped, so the call goes through the session
// layer and would fail before fetch is reached without a token.
describe('documentApi export request contract', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  // The binary success shape: a blob body, read via `res.blob()` rather than `res.json()`. The mock
  // returns a distinct Blob instance so the assertion pins passthrough (the exact server body flows
  // out) rather than merely "some blob".
  function stubExportFetch(blob: Blob): ReturnType<typeof vi.fn> {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: async () => blob,
    })
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  it('exportDocument GETs the export endpoint with the format query param and returns the body', async () => {
    const pdfBlob = new Blob(['%PDF-1.7 binary'], { type: 'application/pdf' })
    const fetchMock = stubExportFetch(pdfBlob)

    const result = await exportDocument('doc-1', 'pdf')

    // Identity, not "some blob": the exact server body flows out untouched.
    expect(result).toBe(pdfBlob)
    const [url, init] = fetchMock.mock.calls[0]
    // Exact URL, not two `toContain`s. The spec is one canonical request line, and only the
    // whole string pins what the loose form leaves open: the query lives at `?format=pdf` (not
    // `&`, not re-ordered behind another param), nothing else rides along, and no stray segment
    // precedes `/export`. API_BASE is '' under Vitest, so the path IS the URL — green must match.
    expect(url).toBe('/api/v1/documents/doc-1/export?format=pdf')
    expect(init.method).toBe('GET')
    // The FULL header set, matching getDocument's convention: a GET carries no body, so no
    // Content-Type, and the assertion pins that negative too — the only header is the session
    // token. Owner-scoped: the backend cannot serve a document to a user it was never told about.
    expect(init.headers).toEqual({ Authorization: 'Bearer access-1' })
  })

  // Safety-critical ordering guard (premortem a227968): the blob body must be read ONLY after the
  // res.ok check. If a future edit hoists the blob read above the guard, a 4xx/5xx error body would
  // stream out and be downloaded AS the document. This pins the invariant: a non-ok response must
  // reject (the shared transport's HttpError) and must NEVER read/return a blob.
  it('exportDocument rejects on a non-ok response and never streams the error body as a blob', async () => {
    const blobSpy = vi.fn(async () => new Blob(['{"error":"boom"}']))
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ message: 'export failed' }),
      blob: blobSpy,
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(exportDocument('doc-1', 'pdf')).rejects.toThrow()
    expect(blobSpy).not.toHaveBeenCalled()
  })
})
