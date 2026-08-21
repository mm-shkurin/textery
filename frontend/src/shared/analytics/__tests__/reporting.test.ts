// Reporting an event: what goes on the wire, and what a failure costs the visitor.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BROWSER_EVENTS, report, resetSendOutcomes, sendOutcomes } from '../analyticsClient'
import { resetTrackers, trackSiteVisit } from '../trackers'
import { forgetVisitor } from '../visitorId'

// Typed as the two arguments this module actually passes, rather than as `fetch`'s full
// overloaded signature: the assertions read `calls[0]` positionally, and a mock typed loosely
// enough to satisfy the DOM lib gives those reads `undefined` at compile time.
type FetchCall = [string, RequestInit]

function fetchMock(response: Partial<Response> | Error) {
  const mock = vi.fn((..._call: FetchCall): Promise<Response> =>
    response instanceof Error ? Promise.reject(response) : Promise.resolve(response as Response),
  )
  vi.stubGlobal('fetch', mock)
  return mock
}

describe('reporting a browser event', () => {
  beforeEach(() => {
    window.localStorage.clear()
    forgetVisitor()
    resetTrackers()
    resetSendOutcomes()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts the event with the visitor, a fresh occurrence key and keepalive', async () => {
    const mock = fetchMock({ ok: true } as Response)

    report(BROWSER_EVENTS.siteVisited)
    await vi.waitFor(() => expect(mock).toHaveBeenCalledTimes(1))

    const [url, init] = mock.mock.calls[0]
    expect(url).toBe('/api/v1/analytics/events')
    expect(init.method).toBe('POST')
    // Without keepalive a visitor who lands and closes the tab is cancelled by the browser and
    // never counted — which is exactly the visit a bounce rate is about.
    expect(init.keepalive).toBe(true)
    const body = JSON.parse(String(init.body))
    expect(body.event_name).toBe('SITE_VISITED')
    expect(body.visitor_id).toMatch(/^[0-9a-f-]{36}$/)
    expect(body.occurrence_key).toMatch(/^[0-9a-f-]{36}$/)
    expect(body.degraded).toBe(false)
  })

  it('mints a DIFFERENT occurrence key per report, so two visits are two events', async () => {
    const mock = fetchMock({ ok: true } as Response)

    report(BROWSER_EVENTS.siteVisited)
    report(BROWSER_EVENTS.editorOpened)
    await vi.waitFor(() => expect(mock).toHaveBeenCalledTimes(2))

    const keys = mock.mock.calls.map(([, init]) => JSON.parse(String(init.body)).occurrence_key)
    expect(keys[0]).not.toBe(keys[1])
  })

  it('is inert when the endpoint refuses, and counts the refusal', async () => {
    fetchMock({ ok: false, status: 429 } as Response)

    expect(() => {
      report(BROWSER_EVENTS.siteVisited)
    }).not.toThrow()

    await vi.waitFor(() => expect(sendOutcomes().refused).toBe(1))
  })

  it('is inert when the endpoint is unreachable, and counts that separately', async () => {
    fetchMock(new TypeError('Failed to fetch'))

    report(BROWSER_EVENTS.siteVisited)

    // Counted rather than swallowed whole: "analytics is silently dead" and "nobody visited"
    // look identical in the data, and only a local tally tells them apart.
    await vi.waitFor(() => expect(sendOutcomes().unreachable).toBe(1))
    expect(sendOutcomes().ok).toBe(0)
  })

  it('reports exactly one site visit per page load', async () => {
    const mock = fetchMock({ ok: true } as Response)

    trackSiteVisit('')
    trackSiteVisit('')

    await vi.waitFor(() => expect(mock).toHaveBeenCalledTimes(1))
  })
})
