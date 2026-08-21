// The visitor identity, and what it does when the browser will not store it.
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { forgetVisitor, visitorIdentity } from '../visitorId'

const KEY = 'textery.analytics.visitorId'
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

describe('the visitor identity', () => {
  beforeEach(() => {
    window.localStorage.clear()
    forgetVisitor()
    vi.restoreAllMocks()
  })

  it('mints a well-formed v4 identity on the first visit and persists it', () => {
    const identity = visitorIdentity()

    expect(identity.visitorId).toMatch(UUID)
    expect(identity.degraded).toBe(false)
    // Persisted, not only returned: the whole point is that tomorrow's visit is the same visitor.
    expect(window.localStorage.getItem(KEY)).toBe(identity.visitorId)
  })

  it('reuses the identity a returning visitor already had', () => {
    const existing = '11111111-2222-4333-8444-555555555555'
    window.localStorage.setItem(KEY, existing)

    expect(visitorIdentity().visitorId).toBe(existing)
  })

  it('replaces a stored value that is not a UUID instead of reporting it', () => {
    // A value the server cannot parse would be refused on every send, forever, for this browser.
    window.localStorage.setItem(KEY, 'not-a-uuid')

    const identity = visitorIdentity()

    expect(identity.visitorId).toMatch(UUID)
    expect(identity.visitorId).not.toBe('not-a-uuid')
    expect(window.localStorage.getItem(KEY)).toBe(identity.visitorId)
  })

  it('still reports, and says so, when the browser refuses to store', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('storage is disabled')
    })

    const identity = visitorIdentity()

    // Not a crash and not an empty id: a browser in private mode is a visitor too. `degraded`
    // is what lets the backend keep these rows out of unique-visitor counts.
    expect(identity.visitorId).toMatch(UUID)
    expect(identity.degraded).toBe(true)
  })

  it('keeps ONE identity across the events of a single load when storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('storage is disabled')
    })

    // Without the per-load cache, the site visit and the registration from one degraded session
    // would arrive as two visitors and every such session would read as a bounce.
    expect(visitorIdentity().visitorId).toBe(visitorIdentity().visitorId)
  })

  it('forgets the identity when the account is deleted', () => {
    const first = visitorIdentity().visitorId

    forgetVisitor()

    expect(window.localStorage.getItem(KEY)).toBeNull()
    expect(visitorIdentity().visitorId).not.toBe(first)
  })
})
