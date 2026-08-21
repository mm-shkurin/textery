// The minter, and specifically its fallback.
//
// `crypto.randomUUID` covers every browser this app is served to, so the fallback never runs in
// production — which is exactly why it needs a test. It runs on an insecure-origin preview build
// and in an environment without the Web Crypto API, and the failure it prevents is a thrown
// TypeError taking a page down for the sake of an analytics identifier. Untested, a fallback that
// mints something the server's `uuid` column refuses would be discovered by a whole preview
// environment reporting nothing.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mintUuid } from '../uuid'

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

describe('minting a uuid', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses the platform generator when there is one', () => {
    const randomUUID = vi.fn(() => '11111111-2222-4333-8444-555555555555')
    vi.stubGlobal('crypto', { randomUUID })

    expect(mintUuid()).toBe('11111111-2222-4333-8444-555555555555')
    expect(randomUUID).toHaveBeenCalledTimes(1)
  })

  it('mints a canonical v4 without the platform generator', () => {
    vi.stubGlobal('crypto', {})

    // The version and variant nibbles are the point: the server column is a native `uuid`, and a
    // value it cannot parse is an event refused on every send, forever, from that browser.
    expect(mintUuid()).toMatch(V4)
  })

  it('mints a different value each time it falls back', () => {
    vi.stubGlobal('crypto', {})

    const minted = new Set(Array.from({ length: 20 }, () => mintUuid()))

    // One shared identity across a preview environment would make every visitor there the same
    // person, which is a worse answer than no analytics at all.
    expect(minted.size).toBe(20)
  })
})
