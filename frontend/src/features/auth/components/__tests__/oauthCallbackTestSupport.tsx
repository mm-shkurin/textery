// What all ten OAuthCallback suites need, in one place.
//
// Each of them mocks the same three seams and renders the same component at the same route, and
// each had hand-copied the navigation spy, the render helper and a promise the exchange never
// settles. That is the shape a reader diffs two files to understand, and the shape a change to the
// callback's route or props has to be applied ten times to.
//
// What CANNOT move here is `vi.mock` itself: the registry is per test file and the calls are
// hoisted above imports, so every suite still declares which seams it takes. What moves is
// everything those declarations point at.
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { OAuthCallback } from '../OAuthCallback'

// One spy per test FILE — vitest gives each file its own module graph, so this is not shared state
// between suites. The `vi.mock` factory in each suite closes over it rather than reading it at
// declaration time, which is why importing it here is safe despite the hoisting.
export const navigate = vi.fn()

export const CALLBACK_ROUTE = '/auth/callback'

// The session the exchange returns on the happy path. A distinctive sentinel: the exchange really
// maps the /auth/login body shape, but it is mocked in these suites, so the value's only job is to
// prove the component pipes what it was given into authSession instead of fabricating its own.
export const SESSION = {
  accessToken: 'acc-9f3ab',
  refreshToken: 'ref-7b2cd',
  accessTokenExpiresAt: '2026-07-22T10:00:00Z',
  refreshTokenExpiresAt: '2026-07-29T10:00:00Z',
}

export function renderCallbackAt(query: string) {
  return render(
    <MemoryRouter initialEntries={[`${CALLBACK_ROUTE}${query}`]}>
      <OAuthCallback />
    </MemoryRouter>,
  )
}

// An exchange whose answer the test controls, for asserting what the screen shows WHILE it is in
// flight — the loading interstitial only exists in that window.
export function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

// An exchange that never answers. Used where the point is that it was never CALLED: a mock left
// returning `undefined` would make the component await a non-promise, so "not called" would pass
// for the wrong reason.
export function neverResolves<T>() {
  return new Promise<T>(() => {})
}
