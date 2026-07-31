import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getDocument, saveDocument } from '../documentApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'
import { describeFailure } from '../../../../shared/api/send'

// What a REFUSED documents call rejects with, and what a person is told about it. Split out of
// `documentApi.test.ts` (which pins the wire mapping and headers) when the H9.4 `send` carve-out
// pushed that file over the 200-line limit — the two concerns had already grown apart: everything
// here is about the error channel, and after H9.4 that channel has two shapes rather than one.
describe('documentApi error text', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  function stubRefusal(status: number, body: unknown): void {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status, json: async () => body }))
  }

  // Deliberately 500, not 409: 409 is no longer a refusal to report but a protocol step the
  // client recovers from (`documentApi.conflict.test.ts`). Using it here would assert the message
  // of an error the user is never shown.
  //
  // RE-POINTED 2026-07-28 (H9.4), NOT relaxed. This was `rejects.toThrow('Внутренняя ошибка
  // сервера')`. `send` now rethrows 5xx as the bare `HttpError` OBJECT so the autosave retry
  // policy can read `.status`, and a plain-object rejection does not satisfy `rejects.toThrow` —
  // there is no `Error` here to carry a message. The claim this test always made is unchanged and
  // still asserted, in the two halves it split into: the rejection CARRIES the server's message
  // (now in `body`, where it can no longer be lost to a string), and rendering it through the
  // helper every consumer calls still produces that exact text. Asserting only the shape would
  // drop the last message-level assertion at this seam — precisely how a 500 could start showing
  // users a generic string with nothing red.
  it('saveDocument rejects with the server error message on a non-OK response', async () => {
    stubRefusal(500, { message: 'Внутренняя ошибка сервера' })

    const rejection = await saveDocument('doc-1', '<p>Hello</p>', 1).catch((e: unknown) => e)

    expect(rejection).toEqual({ status: 500, body: { message: 'Внутренняя ошибка сервера' } })
    expect(describeFailure(rejection, 'Не удалось сохранить')).toBe('Внутренняя ошибка сервера')
  })

  // 4xx still FLATTENS: a decided answer no caller has to classify, so it keeps arriving as a
  // real `Error` and `rejects.toThrow` still applies. Pinning both sides of the carve-out here
  // is what stops it being widened to every status.
  it('getDocument rejects with server error detail on non-OK response', async () => {
    stubRefusal(404, { detail: 'Документ не найден' })

    await expect(getDocument('doc-1')).rejects.toThrow('Документ не найден')
  })
})
