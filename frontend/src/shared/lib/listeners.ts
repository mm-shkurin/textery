// The subscribe/notify half of a `useSyncExternalStore` store, written once.
//
// Three stores — identity, avatar, theme — each kept their own `Set`, their own subscribe function
// returning its own unsubscribe closure, and their own `for (const listener of [...listeners])`.
// The bodies were identical, and the one detail in them that is easy to get wrong was therefore
// copied three times rather than decided once: notifying over a COPY of the set. A listener that
// unsubscribes while being notified — which is exactly what React does when a subscribed component
// unmounts during a re-render — mutates the set mid-iteration, and the next listener is skipped.
//
// What is deliberately NOT here is the value. Each store owns its own state and its own snapshot
// rules (identity's object identity, theme's plain string, the avatar's revocable URL), and a
// generic `createStore<T>` would have to be told about all three.
export interface ListenerSet {
  subscribe: (listener: () => void) => () => void
  notify: () => void
  // Read by the identity store to decide whether a refetch is worth making: nobody subscribed
  // means every component that would display the value has unmounted.
  size: () => number
}

export function listenerSet(): ListenerSet {
  const listeners = new Set<() => void>()
  return {
    subscribe(listener) {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },
    notify() {
      for (const listener of [...listeners]) listener()
    },
    size: () => listeners.size,
  }
}
