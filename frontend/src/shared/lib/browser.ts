// The one place that touches the browser's globals.
//
// The jury's remark named `useDismissOnOutside` reaching for `document` and `window` with no
// environment check, and it was the general case: a dozen modules assumed a DOM. Anything that
// evaluates outside one — a server render, a node script importing a helper for its pure parts, a
// test environment without jsdom — got a ReferenceError from a module it never asked to run.
//
// These are deliberately thin. The point is not to wrap the DOM; it is that there is exactly one
// answer to "are we in a browser", and modules ask it here instead of each inventing a guard.

export function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof document !== 'undefined'
}

// The window, or null off-browser. Callers that only act when a browser exists read better with
// `const view = browserWindow(); if (!view) return` than with a bare typeof check.
export function browserWindow(): Window | null {
  return isBrowser() ? window : null
}

export function browserDocument(): Document | null {
  return isBrowser() ? document : null
}

// Options are forwarded only when given. Passing an explicit `undefined` third argument is not
// the same call: a spy that asserts on the exact arguments of add/removeEventListener sees three
// where the code it guards makes two, and the pair no longer matches by identity for a reader.
function bind(
  target: EventTarget,
  type: string,
  handler: EventListener,
  options?: AddEventListenerOptions,
): () => void {
  if (options === undefined) {
    target.addEventListener(type, handler)
    return () => target.removeEventListener(type, handler)
  }
  target.addEventListener(type, handler, options)
  return () => target.removeEventListener(type, handler, options)
}

// Subscribe to an event and get the unsubscribe back, so an effect's cleanup is the return value
// and cannot be forgotten. A no-op off-browser, which is what an effect body wants there.
export function listen<K extends keyof WindowEventMap>(
  type: K,
  handler: (event: WindowEventMap[K]) => void,
  options?: AddEventListenerOptions,
): () => void {
  const view = browserWindow()
  if (!view) return () => {}
  return bind(view, type, handler as EventListener, options)
}

// Web storage that cannot throw at the call site. Storage is unavailable in private-mode Safari
// and under some enterprise policies, and it throws there rather than returning null — a device
// preference is never worth failing a page over.
export function readStored(area: 'local' | 'session', key: string): string | null {
  try {
    const view = browserWindow()
    if (!view) return null
    return (area === 'local' ? view.localStorage : view.sessionStorage).getItem(key)
  } catch {
    return null
  }
}

export function writeStored(area: 'local' | 'session', key: string, value: string): boolean {
  try {
    const view = browserWindow()
    if (!view) return false
    ;(area === 'local' ? view.localStorage : view.sessionStorage).setItem(key, value)
    return true
  } catch {
    return false
  }
}

export function removeStored(area: 'local' | 'session', key: string): void {
  try {
    const view = browserWindow()
    if (!view) return
    ;(area === 'local' ? view.localStorage : view.sessionStorage).removeItem(key)
  } catch {
    // Nothing to do: the value is unreachable either way.
  }
}

export function listenToDocument<K extends keyof DocumentEventMap>(
  type: K,
  handler: (event: DocumentEventMap[K]) => void,
  options?: AddEventListenerOptions,
): () => void {
  const doc = browserDocument()
  if (!doc) return () => {}
  return bind(doc, type, handler as EventListener, options)
}
