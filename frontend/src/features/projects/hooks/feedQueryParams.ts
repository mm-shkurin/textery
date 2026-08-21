// The feed's three coordinates, as they live in the query string.
//
// They are here rather than in component state so opening a project and coming back — or
// refreshing, or sharing the link — re-renders the same filtered feed instead of an unfiltered
// page 1.

export interface FeedParams {
  q: string
  sort: string
  page: number
}

export interface FeedParamsPatch {
  q?: string
  sort?: string
  page?: number
}

export function readFeedParams(params: URLSearchParams): FeedParams {
  // A hand-typed `?page=abc` is not a page. Falling back to 1 keeps `page=NaN` off the wire.
  const requested = Number(params.get('page') ?? '1')
  return {
    q: params.get('q') ?? '',
    sort: params.get('sort') ?? 'created_desc',
    page: Number.isFinite(requested) && requested >= 1 ? Math.trunc(requested) : 1,
  }
}

// The patch applied to the current query string, as a NEW URLSearchParams — the caller decides
// how to install it.
export function mergeFeedParams(params: URLSearchParams, next: FeedParamsPatch): URLSearchParams {
  const merged = new URLSearchParams(params)
  if (next.q !== undefined) {
    // An empty box is the absence of a search, not a search for "". Deleting the parameter
    // keeps the restored URL identical to the one a user who never searched would have.
    if (next.q === '') merged.delete('q')
    else merged.set('q', next.q)
  }
  if (next.sort !== undefined) merged.set('sort', next.sort)
  // Changing the query or the order returns to page 1. Keeping the number is the classic bug:
  // the user lands on an empty page 4 of a 3-page result and reads it as "nothing found".
  if (next.page !== undefined) merged.set('page', String(next.page))
  else if (next.q !== undefined || next.sort !== undefined) merged.delete('page')
  return merged
}
