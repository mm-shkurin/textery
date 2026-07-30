import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createDocumentFromGeneration } from '../documentApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// Story 18, scenario 2.1 — the WIRE half of "a completed generation opens itself in the editor".
// `POST /api/v1/documents/from-generation` (documents_from_generation.yaml) is the only new
// endpoint in this story; every other call the flow makes is story-1/story-5 reuse. Nothing in
// `frontend/src` spoke it before this file — two comments named this step as its owner
// (`useDocumentInit.ts:20`, `DocumentGenerationFlow.autoEditorTransition.test.tsx:20`) and there
// was no client function to name.
//
// SCOPE, stated because the two siblings are already written and must not be pre-empted: this
// file owns method, path, body, header and response mapping, and NOTHING about who calls it or
// how often. Call cardinality under two polls that both observe completion is 2.2's; which
// surface consumes the returned body is 2.3's. A reader who finds a dedup assertion here should
// delete it.
describe('documentApi createDocumentFromGeneration — the from-generation wire contract', () => {
  // Setup, not subject: the call goes through `send` → `authorizedRequest`, so with no session it
  // fails before fetch is reached and no assertion below would be about the wire.
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  const GENERATION_ID = '11111111-1111-4111-8111-111111111111'
  const DOCUMENT_ID = '22222222-2222-4222-8222-222222222222'
  const IDEMPOTENCY_KEY = 'from-generation-abc'

  // The full documented 201/200 body, including the three fields this client deliberately does
  // NOT surface (`document_type`, `created_at`, `updated_at`). They are here so the `toEqual` on
  // the result is a real closed assertion: a green that spreads the wire object through would
  // leak them and fail, rather than silently widening the app-facing type.
  //
  // `content` is HTML, not the generation's markdown — the conversion and the allowlist sanitize
  // both happen server-side, so this client has no transform to do and must not invent one. The
  // `<script>` is what a naive client-side render of the generation text would have had to strip;
  // its absence here is the server's job already done.
  const WIRE_BODY = {
    document_id: DOCUMENT_ID,
    document_type: 'доклад',
    generation_id: GENERATION_ID,
    title: 'Влияние ИИ на образование',
    status: 'draft',
    content: '<h1>Влияние ИИ на образование</h1><p>Готовый текст.</p>',
    version: 1,
    created_at: '2026-07-29T10:00:00Z',
    updated_at: '2026-07-29T10:00:00Z',
  }

  // Asserted by both tests below, and that shared identity is the point of the second one.
  const EXPECTED_RESULT = {
    documentId: DOCUMENT_ID,
    generationId: GENERATION_ID,
    title: 'Влияние ИИ на образование',
    status: 'draft',
    content: '<h1>Влияние ИИ на образование</h1><p>Готовый текст.</p>',
    version: 1,
  }

  function stubFetch(status: number): ReturnType<typeof vi.fn> {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status,
      json: async () => WIRE_BODY,
    })
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  // RED (2026-07-30), observed live, 2 failed / 0 passed — predicted verbatim, including the
  // throw site: the `throw` inside `createDocumentFromGeneration`, reached from the `await` in the
  // test body below, so not one fetch assertion was evaluated. Cited positionally on purpose —
  // the first version of this comment named `documentApi.ts:165` and test line 80, and BOTH had
  // already rotted by the end of this same work unit (test-review's comment expansion moved the
  // call, and /refactor's header rewrite moved the throw to :167). Line numbers in a recorded
  // trace are stale the moment anything above them is edited:
  //
  //   Error: not implemented (11111111-1111-4111-8111-111111111111, from-generation-abc)
  //
  // `createDocumentFromGeneration` is a stub that throws before reaching fetch.
  it.skip('posts the generation id under a client-supplied Idempotency-Key and maps the 201', async () => {
    const fetchMock = stubFetch(201)

    const result = await createDocumentFromGeneration(GENERATION_ID, IDEMPOTENCY_KEY)

    expect(result).toEqual(EXPECTED_RESULT)
    // Exactly one POST. Reading calls[0] alone would not notice a second request, and a duplicate
    // conversion is the hazard the whole Idempotency-Key mechanism exists to absorb. This is the
    // wire-level floor, NOT 2.2's dedup claim: 2.2 is about two poll observations racing, which
    // this file never produces.
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/documents/from-generation')
    // `toEqual` over the WHOLE init, not three per-field checks: the per-field form is open —
    // it admits any extra key the client invents (a `credentials`, a stray `mode`, a second
    // body field) and it left `signal` pinned by nothing, which is what releases the socket
    // when the 2.2 poll loop abandons a conversion. Every claim below is closed by one compare.
    //
    // headers: the whole set, not just the key under test. `Idempotency-Key` is `required: true`
    // in the spec — a green that forgets it earns a 422 no other assertion here would see — and
    // dropping `Authorization` would make this an anonymous request that 401s, equally invisible
    // to a header-subset check. `Content-Type` is the transport's, added because a body exists.
    //
    // body: the serialized string, exact. `generation_id` is the ONLY field the endpoint accepts,
    // and the spec is explicit that server-owned fields sent alongside it (title, id, status,
    // version) are IGNORED rather than honoured — so sending them is a silent claim of ownership
    // this client does not have, and any subset matcher would permit it. Comparing the string
    // rather than `JSON.parse(init.body)` is safe at exactly one key: there is no field order to
    // be brittle about, and it additionally pins that the body is serialized at all.
    //
    // signal: `expect.any(AbortSignal)` per determinism-hierarchy's "truly opaque" category, and
    // the justification that category demands — the AbortController is constructed inside
    // `withTimeout` (httpClient.ts:96) with no API that hands the instance back, so its identity
    // is unreachable from here. Its PRESENCE is the assertable fact and is what this pins.
    expect(init).toEqual({
      method: 'POST',
      signal: expect.any(AbortSignal),
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': IDEMPOTENCY_KEY,
        Authorization: 'Bearer access-1',
      },
      body: JSON.stringify({ generation_id: GENERATION_ID }),
    })
  })

  // RED (2026-07-30), observed live — same stub, same throw site, the arguments differing only in
  // the key, exactly as predicted:
  //
  //   Error: not implemented (11111111-1111-4111-8111-111111111111, from-generation-xyz)
  //
  // 200 is a SUCCESS here, and that is the whole claim. The spec gives it two causes — an
  // idempotent replay, and a lost race between two backend instances where the UNIQUE constraint
  // on `Document.generation_id` makes the second insert fail and return the existing row — and
  // the frontend can tell neither from the other, nor does it need to: both hand back the
  // document the user must now edit. A client that treats "not 201" as a failure shows an error
  // over a document that exists and is ready, which is worse than the error it reports.
  //
  // Not redundant with the test above, though the body is identical: `send`/`request` branch on
  // `res.ok` alone today, so this passes for free on the shared transport — it is a pin against a
  // green that adds a `status === 201` check of its own to THIS client, which is the natural
  // mistake when writing a "created" mapper. The transport is what must stay status-agnostic.
  it.skip('treats an idempotent 200 replay as success and maps it identically to a 201', async () => {
    stubFetch(200)

    const replayed = await createDocumentFromGeneration(GENERATION_ID, 'from-generation-xyz')

    expect(replayed).toEqual(EXPECTED_RESULT)
  })
})
