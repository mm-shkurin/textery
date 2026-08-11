// Test-support for `editorDocumentApi.test.ts`: the fetch stub, the error-identity assertion, and
// the wire fixtures. Split out on the 200-line limit, along the seam that costs nothing — the test
// file keeps all five cases and its single `describe.skip` marker, and what moved here is the
// machinery none of them narrate.
//
// Mirrors `auth/api/__tests__/loginApiTestUtils.ts`. As there, no `vi.mock` lives here: module
// mocks are hoisted and file-scoped and must stay in the test file.
import { expect, vi } from 'vitest'

// The default implementation THROWS rather than returning undefined. An unstubbed extra call would
// otherwise resolve to `undefined` and blow up inside httpClient on `res.ok`, turning "the client
// made a request this test never authorised" into an unreadable TypeError. Each test also pins the
// exact call list, so an extra call is a failure and not a shrug.
export function stubFetch(...responses: unknown[]): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn()
  fetchMock.mockImplementation(() => {
    throw new Error('fetch called more times than the test stubbed')
  })
  responses.forEach((response) => fetchMock.mockResolvedValueOnce(response))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

// The three claims every refusal case makes about the thrown value, in one place because they only
// mean something together: the CLASS is what `useEditorDocument` branches on, the `name` is what
// survives a green that re-declares the class in a second module (two structurally identical
// classes, one `instanceof` that silently goes false), and the MESSAGE is what separates a raised
// class from an implementation that merely echoes `body.message`. Dropping any one of the three
// re-opens a green that the other two let through — so they travel together.
export function expectErrorIdentity(
  error: unknown,
  type: new (...args: never[]) => Error,
  name: string,
  message: string,
): void {
  expect(error).toBeInstanceOf(type)
  expect((error as Error).name).toBe(name)
  expect((error as Error).message).toBe(message)
}

// A 200 carrying `body`. Shared rather than re-declared per test file: the shape is pure transport
// machinery no case narrates, and a local copy in each file is a second place for the `ok`/`status`
// pair to drift out of agreement with what httpClient actually branches on (`res.ok`).
export function okJson(body: unknown): { ok: true; status: 200; json: () => Promise<unknown> } {
  return { ok: true, status: 200, json: async () => body }
}

// VITE_API_BASE_URL is empty (frontend/.env), so httpClient's API_BASE is '' and the fetched URL is
// the path verbatim. Asserted with toBe, not toContain: `toContain` passes for
// '/api/v1/documents/doc-1/versions' and for a doubled base, which are different endpoints.
export const DOCUMENT_URL = '/api/v1/documents/doc-1'
export const REFRESH_URL = '/api/v1/auth/refresh'
// Account-scoped, NOT '/api/v1/documents/{id}/ai-edits/quota'. Lives here beside its peers so the
// endpoint table has one home rather than two.
export const QUOTA_URL = '/api/v1/ai-edits/quota'

// The 401 both API test files drive their renew-and-replay case with. Stubbed twice per case: the
// first is the original request, the second is the refresh, whose failure is the only path that
// reaches a caller as SessionExpiredError.
export const UNAUTHORIZED_RESPONSE = {
  ok: false,
  status: 401,
  json: async () => ({ error_code: 'UNAUTHORIZED', message: 'Unauthorized' }),
}
export const SESSION_EXPIRED_MESSAGE = 'Сессия истекла. Войдите снова.'

// The wire text is deliberately NOT the Russian sentence the error carries. DocumentNotFoundError
// is constructed with no arguments and owns its message, so asserting the Russian constant while
// the body says something else proves the class was raised — where matching bodies would also pass
// for an implementation that merely echoes `body.message` into a plain Error.
export const NOT_FOUND_RESPONSE = {
  ok: false,
  status: 404,
  json: async () => ({ error_code: 'NOT_FOUND', message: 'Document not found' }),
}
export const NOT_FOUND_MESSAGE = 'Документ не найден'
