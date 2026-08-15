import { useEffect, type RefObject } from 'react'
import { listenToDocument } from '../lib/browser'

// Closes a transient overlay the two ways a user expects to close one: clicking away from it, and
// pressing Escape. Both listeners are on `document` because the gesture that dismisses a popup
// happens, by definition, outside the popup — a handler on the panel itself never sees it.
//
// `mousedown`, not `click`: a click fires after the press, so a press that lands on a button
// elsewhere on the page would dismiss the menu and activate that button in the same gesture only
// if the dismissal happens first. Dismissing on the press keeps the two in that order.
//
// Nothing is bound while `active` is false — an idle menu must not make every click on the page
// pay for a listener, and the effect's cleanup is the only thing guaranteeing the listeners go
// away with the component.
export function useDismissOnOutside(
  active: boolean,
  containerRef: RefObject<HTMLElement | null>,
  dismiss: () => void,
): void {
  useEffect(() => {
    if (!active) return

    const handlePointerDown = (event: MouseEvent) => {
      const container = containerRef.current
      if (container !== null && !container.contains(event.target as Node)) dismiss()
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') dismiss()
    }

    // Through `listenToDocument` rather than `document` directly: the hook is imported by modules
    // that can be evaluated without a DOM, and each subscription hands back its own unsubscribe,
    // so the cleanup below cannot drift out of step with what was bound.
    const stopPointer = listenToDocument('mousedown', handlePointerDown)
    const stopKeys = listenToDocument('keydown', handleKeyDown)

    return () => {
      stopPointer()
      stopKeys()
    }
  }, [active, containerRef, dismiss])
}
