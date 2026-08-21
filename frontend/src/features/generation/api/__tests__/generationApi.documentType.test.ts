import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createGeneration } from '../generationApi'
import { clearSession, saveSession } from '../../../../shared/session/authSession'

// Story 18, scenario 1.1 — "picking a document type goes straight to generation".
//
// Removing the mode modal made the type card the LAST thing the user picks before a generation
// is created, which puts the whole weight of that choice on one wire field. `createGeneration`
// takes only a topic and hardcodes WIRE_DOCUMENT_TYPE[DEFAULT_DOCUMENT_TYPE], so whatever card
// the user pressed, the backend is asked for a доклад. Today that is invisible — 'doklad' is the
// only card with `available: true` — but it is the exact defect scenario 1.1 is about: the type
// the user picked must be the type that gets generated, and nothing anywhere asserts that.
//
// `documentApi.createDocument(documentType, ...)` already takes the type and maps it; this is
// the same boundary translation missing on the generation side.
describe('generationApi createGeneration — the picked document type reaches the wire', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  // RED (2026-07-28): createGeneration(topic) ignores any second argument and always sends
  // document_type 'доклад'.
  // Predicted: AssertionError — expected 'доклад' to be 'реферат'.
  it('sends the type the user picked, not the default', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ generation_id: 'gen-1', status: 'pending' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    // Pinned so the key is a value this test DEFINES rather than an opaque one it declines to
    // check. It is load-bearing: the same key on a 401-replay is what collapses the replay onto
    // one generation instead of billing the user for two.
    vi.stubGlobal('crypto', { randomUUID: () => 'idem-1' })

    const result = await createGeneration('Тема', 'referat')

    expect(result).toEqual({ generationId: 'gen-1', status: 'pending' })
    // Exactly one POST. Reading calls[0] alone would not notice a duplicate — two generations
    // for one click is precisely the hazard the Idempotency-Key exists to absorb.
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/generations')
    expect(init.method).toBe('POST')
    // Whole header set, not just the one under test: dropping Authorization would make this an
    // anonymous request that no other assertion here would catch.
    expect(init.headers).toEqual({
      'Content-Type': 'application/json',
      'Idempotency-Key': 'idem-1',
      Authorization: 'Bearer access-1',
      // The analytics visitor id, so the backend can attribute this generation's start and its
      // later completion to the browser that asked. Same stubbed `crypto.randomUUID` as the
      // idempotency key, hence the identical value -- the assertion that matters here is that
      // the header is PRESENT, since a request without it silently drops the visitor from the
      // funnel while every other assertion stays green.
      'X-Visitor-Id': 'idem-1',
    })
    // The Cyrillic wire value, not the app-internal id — the backend 422s on 'referat'.
    // toEqual over the whole body, not toMatchObject: a dropped, renamed, or extra wire field
    // must fail here, and volume_pages is required by the endpoint.
    expect(JSON.parse(init.body)).toEqual({
      document_type: 'реферат',
      topic: 'Тема',
      volume_pages: 5,
    })
  })
})
