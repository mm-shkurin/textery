import { afterEach, describe, expect, it, vi } from 'vitest'
import { createDocument, saveDocument } from '../documentApi'
import { API_BASE } from '../httpClient'

describe('documentApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('createDocument posts document_type and returns documentId + status', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ document_id: 'doc-1', status: 'draft', content: '', version: 1 }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await createDocument('doklad')

    expect(result).toEqual({ documentId: 'doc-1', status: 'draft' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/v1/documents')
    expect(init.method).toBe('POST')
    // Idempotency-Key is generated per-call via crypto.randomUUID() (see
    // generationApi.ts's createGeneration for the established pattern) — the
    // value itself is opaque, but its shape must be an actual UUID, not merely truthy.
    expect(init.headers).toEqual({
      'Content-Type': 'application/json',
      'Idempotency-Key': expect.stringMatching(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i),
    })
    expect(JSON.parse(init.body)).toEqual({
      document_type: 'doklad',
      content: '',
    })
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
})
