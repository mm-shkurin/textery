import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { projectsQueryKey, useProjectsFeedCache } from '../hooks/useProjectsFeedCache'
import type { ProjectPage } from '../api/projectsApi'
import { DOCUMENT, GENERATION } from '../components/__tests__/projectFixtures'

const KEY = { q: '', sort: 'created_desc', page: 1 }

// The page the user is looking at, seeded directly into the cache: this hook's whole claim is that
// «Повторить» patches THAT entry rather than asking the server for the list again.
const SEEDED: ProjectPage = {
  items: [DOCUMENT, GENERATION],
  total: 2,
  page: 1,
  limit: 20,
}

function harness() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(projectsQueryKey(KEY), SEEDED)
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  const { result } = renderHook(() => useProjectsFeedCache(KEY), { wrapper })
  return { client, result }
}

describe('useProjectsFeedCache', () => {
  it('patches the retried generation in place and refreshes the feed behind it', async () => {
    const { client, result } = harness()
    const invalidate = vi.spyOn(client, 'invalidateQueries')

    await act(async () => result.current.markRetried(GENERATION.id))

    const patched = client.getQueryData<ProjectPage>(projectsQueryKey(KEY))
    // The generation is running again and can no longer be retried — both facts, not just one:
    // a row left `retryable` invites a second click that bills a second generation.
    expect(patched?.items[1]).toEqual({ ...GENERATION, status: 'pending', retryable: false })
    // The DOCUMENT shares the generation's id on purpose (see projectFixtures): a patch keyed on
    // the id alone would rewrite the wrong row, and it comes from the other table entirely.
    expect(patched?.items[0]).toEqual(DOCUMENT)
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['projects'] })
  })

  // An empty cache is the ordinary case for a retry fired from a page that has since been dropped.
  // Writing a fabricated page there would paint a row the server never sent.
  it('leaves an absent page absent', async () => {
    const { client, result } = harness()
    client.removeQueries({ queryKey: projectsQueryKey(KEY) })

    await act(async () => result.current.markRetried(GENERATION.id))

    expect(client.getQueryData(projectsQueryKey(KEY))).toBeUndefined()
  })

  it('marks every cached feed page stale on an explicit reload', async () => {
    const { client, result } = harness()
    const invalidate = vi.spyOn(client, 'invalidateQueries')

    await act(async () => result.current.reload())

    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['projects'] })
  })
})
