import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { retryGeneration, RETRY_FAILURE_FALLBACK } from '../retryGenerationApi'
import { clearSession, saveSession } from '../../../../shared/session/authSession'
import { settle, stubFetchJson } from './projectsWireFixtures'

// The «Повторить» endpoint, at the transport.
//
// It had no test of its own. `useRetryGeneration`'s two suites both `vi.mock` this module, so
// everything below the hook — the method, the path, the header the whole idempotency story rests
// on, the absence of a body — was asserted by nobody. That is the same hole `historyApi.ts` sat in
// at 0% while every caller mocked it, which is what the per-file coverage floor exists to catch;
// this module passed the floor on its exported constants alone.
//
// What makes this worth a suite rather than a formality: THIS is the app's one paid operation. A
// second POST that reaches the server without the same `Idempotency-Key` is a second generation
// the user is billed for, and the header is the only thing standing between a retried click and
// that. A mock cannot fail if the header is dropped here.
//
// The path is written out on this side rather than imported from the module under test. A test
// that reads the endpoint from its subject pins nothing — the URL could change to anything and
// this would still pass. Same rule as projectsWireFixtures' FEED_PATH, one directory over.
const GENERATION_ID = '9f1c2b74-0000-4000-8000-00000000abcd'
const RETRY_PATH = `/api/v1/generations/${GENERATION_ID}/retry`

// The refusal half of the transport stub. `stubFetchJson` only builds ok responses, and this needs
// both a 4xx (flattened to text) and a 5xx (kept as an HttpError) - the two arms `send` treats
// differently and the whole point of the last two cases.
function stubFetchFailure(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status, json: async () => body }))
}

describe('retryGenerationApi', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('posts to the generation retry path carrying the caller minted idempotency key', async () => {
    const fetchMock = stubFetchJson({ id: 'gen-2', status: 'queued' })

    const response = await retryGeneration(GENERATION_ID, 'key-abc')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(RETRY_PATH)
    expect(init.method).toBe('POST')
    // Read out of the headers as sent, not compared against an object literal: `send` folds
    // authorization in beside it, so an exact-object assertion would pin that unrelated detail
    // and would have to be edited every time the transport gains a header.
    expect(new Headers(init.headers).get('Idempotency-Key')).toBe('key-abc')
    // No body when the caller named no overrides, and this is a contract rather than an
    // omission. The server copies every other parameter from the stored source row, so the
    // narrow body is what stops a client binding an owner, a status or a document link to a
    // generation it does not own — and a request that sends `{}` is still a request the plain
    // «Повторить» had no reason to make.
    expect(init.body).toBeUndefined()
    expect(response).toEqual({ id: 'gen-2', status: 'queued' })
  })

  it('carries a register override under its contract name', async () => {
    const fetchMock = stubFetchJson({ id: 'gen-2', status: 'queued' })

    await retryGeneration(GENERATION_ID, 'key-abc', { textStyle: 'научный' })

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ text_style: 'научный' })
  })

  it('carries a length override as an integer under its contract name', async () => {
    const fetchMock = stubFetchJson({ id: 'gen-2', status: 'queued' })

    await retryGeneration(GENERATION_ID, 'key-abc', { volumePages: 8 })

    // A number, not the string the picker reports: the wire field is an integer and a string is
    // a 422 the user cannot act on from a card.
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ volume_pages: 8 })
  })

  it('carries both overrides when both were chosen', async () => {
    const fetchMock = stubFetchJson({ id: 'gen-2', status: 'queued' })

    await retryGeneration(GENERATION_ID, 'key-abc', { textStyle: 'научный', volumePages: 2 })

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      text_style: 'научный',
      volume_pages: 2,
    })
  })

  it('omits the override the caller did not name rather than sending it null', async () => {
    const fetchMock = stubFetchJson({ id: 'gen-2', status: 'queued' })

    await retryGeneration(GENERATION_ID, 'key-abc', { volumePages: 4 })

    // An explicit null is a client saying «clear this», which would strip the register off a
    // generation that had one. Absent means «keep what the failed run used».
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).not.toHaveProperty('text_style')
  })

  it('sends no body for an overrides object with nothing in it', async () => {
    const fetchMock = stubFetchJson({ id: 'gen-2', status: 'queued' })

    await retryGeneration(GENERATION_ID, 'key-abc', {})

    // The card passes `undefined` when both pickers are untouched, but an empty object must reach
    // the same wire request: whether the plain repeat stays bodiless cannot depend on which of
    // two equivalent shapes a caller happened to build.
    expect(fetchMock.mock.calls[0][1].body).toBeUndefined()
  })

  it('sends a different key for a different click rather than minting one of its own', async () => {
    const fetchMock = stubFetchJson({ id: 'gen-2', status: 'queued' })

    await retryGeneration(GENERATION_ID, 'key-first')
    await retryGeneration(GENERATION_ID, 'key-second')

    // The header is what the CALLER passed, both times. A key generated inside this function
    // would be new on every call, so a retry after a lost response would start - and bill - a
    // second generation, which is the one thing the header exists to prevent. Pinning both calls
    // is what makes that a fact about this module rather than about the hook that usually feeds it.
    const keys = fetchMock.mock.calls.map(([, init]) =>
      new Headers(init.headers).get('Idempotency-Key'),
    )
    expect(keys).toEqual(['key-first', 'key-second'])
  })

  it('rejects with the retry fallback, not the feed one, when the refusal carries no text', async () => {
    stubFetchFailure(403, {})

    const settled = await settle(retryGeneration(GENERATION_ID, 'key-abc'))

    // The message is imported from production rather than re-typed, so a reworded string does not
    // redden this. What is pinned is which fallback surfaced: «Не удалось повторить генерацию» and
    // the feed's «Не удалось загрузить проекты» are separate literals in separate modules, and a
    // card that apologises for the wrong operation is the failure this tells apart. The status is
    // appended by `describeFailure` when the body carries no usable text — kept in the assertion
    // because it is the only fact a bug report would have.
    expect(settled).toEqual({
      rejected: true,
      error: new Error(`${RETRY_FAILURE_FALLBACK} (HTTP 403)`),
    })
  })

  it('keeps a 5xx as an HttpError instead of flattening it into a sentence', async () => {
    stubFetchFailure(503, { message: 'Очередь недоступна' })

    const settled = await settle(retryGeneration(GENERATION_ID, 'key-abc'))

    // `send` deliberately rethrows 5xx unflattened: an outcome that is UNKNOWN - the server may
    // or may not have taken the retry - has to keep its status so a caller can decide whether a
    // second click is safe. Flattening it to `new Error(text)` turns that status into a substring
    // and the decision into string matching. Asserted here because this endpoint is the paid one,
    // where «may this have landed?» is a question about the user's money.
    expect(settled).toEqual({
      rejected: true,
      error: { status: 503, body: { message: 'Очередь недоступна' } },
    })
  })
})
