import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { listProjects } from '../projectsApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// Scenario 1.1 — «Мои проекты» feed client. The transport is stubbed: `GET /api/v1/projects`
// does not exist on the backend yet, so nothing here may reach a real server.
//
// Two facts are pinned, and only two: where the request goes, and what the wire turns into.
// Search, sort and paging parameters belong to scenarios 2.x/3.x and are deliberately absent —
// a test that asserted a default `?limit=20` here would pre-decide a contract those scenarios own.
//
// The mapping is the part that can actually be wrong. The OpenAPI contract
// (`ProductSpecification/api-specs/projects_schemas.yaml`) is snake_case on every field, and
// `ProjectSummary` — which `ProjectCard` already reads — is camelCase; `projectsApi.ts` has no
// wire interface at all today, so a client that returned the parsed body untouched would give the
// card `undefined` for `documentType` and `updatedAt` and render a typeless card with an
// "Invalid Date". `toEqual` on the whole page is what makes that impossible: it fails on an
// extra snake_case key just as loudly as on a missing camelCase one.
describe('projectsApi', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  function stubFetchJson(body: unknown): ReturnType<typeof vi.fn> {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => body,
    })
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  // A generation, not a document: it is the arm that carries the fields a document-shaped
  // fixture would leave untested — `can_repeat: true`, and a `preview` that is null while the
  // title is present. Both are server-computed and neither may be re-derived on this side.
  //
  // `document_type` is Cyrillic because that is what the wire actually carries: the frontend
  // asked for Latin ids and the backend kept Cyrillic, so `shared/documentTypes.ts` translates
  // at the boundary (`WIRE_DOCUMENT_TYPE`) and `ProjectCard` calls `documentTypeLabelFromWire`.
  // The mapping under test is a pass-through on this field, so no assertion here can catch a
  // wrong vocabulary — which is exactly why the fixture has to be right: it is what green's
  // implementation, the MSW handlers, and scenario 1.5's unknown-type arm all get read from.
  const PROJECT_WIRE = {
    kind: 'generation',
    id: '9f1c2b74-0000-4000-8000-00000000abcd',
    title: 'Квантовые вычисления',
    preview: null,
    document_type: 'реферат',
    status: 'failed',
    can_repeat: true,
    created_at: '2026-07-15T09:00:00Z',
    updated_at: '2026-07-15T09:00:00Z',
  }

  // RED 2026-08-02 — `listProjects` is still the stub, so this fails with
  // `Error: Not implemented` (projectsApi.ts:45) before `fetch` is ever called. Skipped rather
  // than left failing so the committed green suite stays green; green-frontend-api removes the
  // `.skip`.
  //
  // The Authorization header is asserted here, not left to the `saveSession` in `beforeEach` to
  // imply: the feed is owner-scoped, and a client that sent no header at all would satisfy the
  // path and the mapping test alike while 401-ing against the real backend.
  //
  // What this does NOT pin: that the call goes through `send` -> `authorizedRequest`. A bare
  // `fetch` with a hand-built `Bearer ${getAccessToken()}` satisfies every assertion below, and
  // would then never 401-renew-and-replay — the feed would be the one authenticated screen that
  // breaks on an expired token. Pinning that needs a 401-then-200 stub, which belongs with the
  // rest of the failure surface in scenario 4.2 (`red-frontend-api` there), not here.
  it.skip('sends a GET to the merged feed path carrying the session', async () => {
    const fetchMock = stubFetchJson({ items: [], total: 0, page: 1, limit: 20 })

    await listProjects()

    // Exactly one call, asserted before the call is indexed: the session in `beforeEach` is
    // valid, so nothing here may 401-renew-and-replay. Without this, a client that fired the
    // request twice would satisfy every assertion below on its first call.
    expect(fetchMock).toHaveBeenCalledTimes(1)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/projects')
    expect(init.method).toBe('GET')
    // The whole header object, not just the Authorization key. For a bodyless GET the set is
    // fully determined — `performRequest` adds `Content-Type` only when a body exists
    // (shared/api/httpClient.ts:139) — so an extra header (a stray `Content-Type`, an
    // `Idempotency-Key` copied from documentApi) is a defect this must fail on, not tolerate.
    expect(init.headers).toEqual({ Authorization: 'Bearer access-1' })
    // A feed read carries no payload. Pinned explicitly rather than via the init key set, which
    // would freeze httpClient's internal shape — a module this test does not own.
    expect(init.body).toBeUndefined()
  })

  // RED 2026-08-02 — same stub, same `Error: Not implemented` (projectsApi.ts:45); the mapping
  // this pins does not exist yet, `projectsApi.ts` has no wire interface at all. Removed by
  // green-frontend-api.
  it.skip('maps every project wire field onto its camelCase counterpart', async () => {
    stubFetchJson({ items: [PROJECT_WIRE], total: 1, page: 1, limit: 20 })

    const page = await listProjects()

    expect(page).toEqual({
      items: [
        {
          kind: 'generation',
          id: '9f1c2b74-0000-4000-8000-00000000abcd',
          title: 'Квантовые вычисления',
          preview: null,
          documentType: 'реферат',
          status: 'failed',
          canRepeat: true,
          createdAt: '2026-07-15T09:00:00Z',
          updatedAt: '2026-07-15T09:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      limit: 20,
    })
  })
})
