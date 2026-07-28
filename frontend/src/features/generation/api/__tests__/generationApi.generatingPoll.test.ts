import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getGeneration } from '../generationApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// Story 18, scenario 1.2 — "a generating document shows progress", at the API-CLIENT seam.
//
// The other two layers that cover 1.2 both stop short of this module, and in opposite
// directions. `DocumentGenerationFlow.generatingState.test.tsx` mocks `generationApi` WHOLESALE,
// so it can prove the generating surface renders but can see nothing about the request that
// keeps it honest — URL, method, headers, or what the answer is parsed into. The Selenium test
// gets closer than that, and it is worth being exact about how close: it asserts that exactly
// one distinct status path is polled and that the path's last segment is a UUID
// (`generating_state_statements.py:166-182`), so it WOULD reject an id-less path. What it
// cannot do is check that id against the one the caller holds — the id is minted in the create
// POST's response body, which `Network.requestWillBeSent` does not carry — and it is
// class-level skipped until green-selenium besides.
//
// So this is the one place the poll's REQUEST and its parsed ANSWER are both observable, and
// both are currently unpinned:
//
// (1) `getGeneration(id)` interpolates `id` into the path, and no EXECUTING test asserts it.
//     The two existing `getGeneration` cases in `generationApi.test.ts` read
//     `calls[0][1].headers` and the mapped result; neither looks at `calls[0][0]`. Drop the
//     `${id}` and every test that actually runs still passes — the single assertion that would
//     catch it is the Selenium UUID check above, and that class is skipped — while the client
//     polls a path that is not the user's generation —
//     which surfaces as scenario 1.2's screen never leaving the generating state. A generating
//     state that is permanent is the same pixels as one that is working, so the defect is
//     invisible above this line and gets misread as a slow backend.
//
// (2) The IN-PROGRESS body is not the body those tests use. `generations_get.yaml` documents
//     `content` as "Present only when status is completed", so a real poll answer mid-generation
//     has no `content` key at all — the shape the `?? null` default exists for, and the shape
//     under which `status` must survive as something non-terminal. The one mapping test uses a
//     `completed` body and asserts two of its seven fields.
//
// NOT a red-to-green transition, and that is stated rather than discovered: `getGeneration`
// already threads the id and already maps these fields. This is a characterization pin on the
// premise the Selenium wire assertion rests on, bite-verified below, the same shape as this
// scenario's red-frontend step. green-frontend-api removes the marker only.
describe('generationApi getGeneration — the poll behind the generating state', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  // What a generating document actually answers with: no `content` key (the spec says it appears
  // only on `completed`), and a status the UI must keep waiting on rather than settle.
  const inProgressWire = {
    generation_id: 'gen-42',
    status: 'in_progress',
    document_type: 'доклад',
    topic: 'Квантовые компьютеры',
    volume_pages: 5,
    created_at: '2026-07-28T09:00:00Z',
  }

  // RED, bite-verified: deleting `${id}` from the path in `getGeneration` fails this at the URL
  // assertion — AssertionError: expected '/api/v1/generations/' to be
  // '/api/v1/generations/gen-42'.
  // green-frontend-api removes this marker only.
  it.skip('asks for the generation it was given and reports it as still running', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => inProgressWire })
    vi.stubGlobal('fetch', fetchMock)

    const status = await getGeneration('gen-42')

    // One wire request per call — an internal retry or a duplicated `send` would show up here.
    // Deliberately NOT a claim about hook-level in-flight guarding or per-tick behaviour: this
    // test calls `getGeneration` directly and never involves the hook, so neither is observable
    // at this seam.
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    // The whole point: the id the caller holds is the id on the wire. Equality, not `toContain`
    // — `toContain('/api/v1/generations')` is satisfied by the collection endpoint and by the
    // id-less path this assertion exists to catch.
    expect(url).toBe('/api/v1/generations/gen-42')

    // The WHOLE init by equality, for the same reason the mapped result below is compared whole:
    // asserting `method`, `body` and `headers` one at a time leaves every other key unobserved,
    // and `performRequest` passes fetch four of them. What the recursive form adds over the
    // three separate checks:
    //   - `signal` is pinned as present. It is what releases the socket when the 25s timeout
    //     fires, and under a 5s poll an unwired signal means abandoned connections accumulate —
    //     a leak no per-field assertion here would have noticed. `any(AbortSignal)` rather than
    //     equality because the controller is created per request inside `withTimeout`.
    //   - no EXTRA key can appear. A stray `responseType`, `credentials`, or `mode` growing on
    //     a read request now fails here instead of shipping silently.
    // `body: undefined` states the read carries no payload, and the exact header set states it
    // announces none either — `httpClient` attaches Content-Type only when there IS a body, so
    // a GET that grew one would break both entries at once. The Authorization entry is what
    // makes the poll return the user's own generation rather than a 401 that the resilience
    // path would absorb as a transient miss.
    expect(init).toEqual({
      method: 'GET',
      signal: expect.any(AbortSignal),
      headers: { Authorization: 'Bearer access-1' },
      body: undefined,
    })

    // `toEqual` over the whole mapped object rather than field-by-field: this is the boundary
    // that renames every wire field, so a dropped rename, a leaked snake_case key, or an extra
    // field must fail here. `status` in particular is the field the entire poll state machine
    // branches on and nothing else in the suite pins it through this function — the hook's own
    // tests mock this module out.
    expect(status).toEqual({
      generationId: 'gen-42',
      status: 'in_progress',
      // Absent on the wire, `null` here. The default is real transformation, not a formality:
      // `undefined` would put the generating surface's document area into a different branch
      // than the empty one it is written for.
      content: null,
      topic: 'Квантовые компьютеры',
      volumePages: 5,
      // Passed through RAW — the Cyrillic wire value, not the app id 'doklad'. Asymmetric with
      // `createGeneration`, which maps app to wire. Pinned as-is because it is what ships and no
      // caller reads it today; recorded here so a future reader sees the asymmetry is known
      // rather than accidental.
      documentType: 'доклад',
      createdAt: '2026-07-28T09:00:00Z',
    })
  })
})
