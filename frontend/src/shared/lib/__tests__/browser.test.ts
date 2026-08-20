import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  browserDocument,
  browserWindow,
  isBrowser,
  listen,
  listenToDocument,
  readStored,
  removeStored,
  writeStored,
} from '../browser'

// The one module that decides "are we in a browser". Every other module asks it instead of
// writing its own typeof check, so a wrong answer here is a ReferenceError in a dozen places at
// once — and the off-browser branches are exactly the ones a jsdom test suite never reaches by
// accident. `stubGlobal(undefined)` is what makes them reachable: it is the server render, the
// node script importing a helper for its pure parts.

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('detecting a browser', () => {
  it('reports one when both globals exist', () => {
    expect(isBrowser()).toBe(true)
    expect(browserWindow()).toBe(window)
    expect(browserDocument()).toBe(document)
  })

  it('reports none when the window is missing, and hands back null instead of throwing', () => {
    vi.stubGlobal('window', undefined)

    expect(isBrowser()).toBe(false)
    expect(browserWindow()).toBeNull()
    expect(browserDocument()).toBeNull()
    // Everything reached through those globals degrades instead of throwing: a helper imported
    // for its pure parts must not fail a server render because it also knows about storage.
    expect(readStored('local', 'k')).toBeNull()
    expect(writeStored('local', 'k', 'v')).toBe(false)
    expect(() => removeStored('local', 'k')).not.toThrow()
    expect(() => listen('resize', vi.fn())()).not.toThrow()
    expect(() => listenToDocument('click', vi.fn())()).not.toThrow()
  })

  it('reports none when the document is missing', () => {
    vi.stubGlobal('document', undefined)

    expect(isBrowser()).toBe(false)
  })
})

describe('subscribing', () => {
  it('forwards listener options and removes the listener with the same ones', () => {
    const add = vi.spyOn(window, 'addEventListener')
    const remove = vi.spyOn(window, 'removeEventListener')
    const handler = vi.fn()
    const options = { capture: true }

    const unsubscribe = listen('resize', handler, options)

    expect(add).toHaveBeenCalledWith('resize', handler, options)
    unsubscribe()
    // Same options object, not a fresh equal one: the browser matches a removal by the capture
    // flag, so a listener added capturing and removed bubbling stays subscribed forever.
    expect(remove).toHaveBeenCalledWith('resize', handler, options)
  })

  it('makes a two-argument call when no options are given', () => {
    const add = vi.spyOn(window, 'addEventListener')
    const handler = vi.fn()

    listen('resize', handler)

    expect(add).toHaveBeenCalledWith('resize', handler)
  })

  it('delivers the event to the handler', () => {
    const handler = vi.fn()

    const unsubscribe = listen('resize', handler)
    window.dispatchEvent(new Event('resize'))
    unsubscribe()
    window.dispatchEvent(new Event('resize'))

    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('subscribes to the document and unsubscribes from it', () => {
    const handler = vi.fn()

    const unsubscribe = listenToDocument('click', handler)
    document.dispatchEvent(new Event('click'))
    unsubscribe()
    document.dispatchEvent(new Event('click'))

    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('is a no-op off-browser, and its cleanup is still callable', () => {
    vi.stubGlobal('window', undefined)
    vi.stubGlobal('document', undefined)

    expect(() => listen('resize', vi.fn())()).not.toThrow()
    expect(() => listenToDocument('click', vi.fn())()).not.toThrow()
  })
})

describe('web storage that cannot throw', () => {
  it('round-trips a value through each area and removes it', () => {
    expect(writeStored('local', 'k', 'v')).toBe(true)
    expect(readStored('local', 'k')).toBe('v')
    removeStored('local', 'k')
    expect(readStored('local', 'k')).toBeNull()

    expect(writeStored('session', 'k', 's')).toBe(true)
    expect(readStored('session', 'k')).toBe('s')
    removeStored('session', 'k')
    expect(readStored('session', 'k')).toBeNull()
  })

  it('answers with null/false when storage itself throws — private mode, enterprise policy', () => {
    // Storage is not merely empty there: getItem THROWS, which is why every call is wrapped.
    const boom = () => {
      throw new Error('access denied')
    }
    // Patched on the prototype, not on the `localStorage` instance: jsdom's storage object
    // exposes its methods there, and a spy set on the instance is simply not the function the
    // call reaches.
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(boom)
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(boom)
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(boom)

    expect(readStored('local', 'k')).toBeNull()
    expect(writeStored('local', 'k', 'v')).toBe(false)
    expect(() => removeStored('local', 'k')).not.toThrow()
  })
})
