import { useEffect, useRef } from 'react'
import type { Tab } from './HistoryPage'

const TABS: Tab[] = ['documents', 'generations']

// The tab half of the tablist/tabpanel pair. `role="tab"` is a promise about keyboard behaviour,
// not a styling hook: a reader who meets it expects arrow keys to move between tabs and Tab to
// leave the list. Previously it made the promise and delivered none of it — no ids, no
// aria-controls, and every tab in the tab order.
export function TabButton({
  id,
  active,
  onSelect,
  label,
}: {
  id: Tab
  active: Tab
  onSelect: (t: Tab) => void
  label: string
}) {
  const isActive = active === id
  const ref = useRef<HTMLButtonElement>(null)

  // Focus follows selection, and that is not a flourish — it is the half that makes the rest
  // true. Roving tabindex gives the SELECTED tab `tabIndex={0}` and every other `-1`, so an
  // arrow press that only changed `active` left the keyboard sitting on the now-deselected
  // button, which had just become unreachable: nothing was announced, and the next Tab jumped
  // from a -1 element. The tablist claimed to be one tab stop while quietly having none.
  useEffect(() => {
    if (!isActive) return
    // ONLY when the keyboard was already on another tab. On mount the focus is elsewhere entirely
    // (body, or whatever the user was using) and grabbing it would be a page that snatches the
    // caret; on a click the browser has already focused the tab that was clicked. The arrow-key
    // path is the one case where selection moved and focus did not follow it.
    const focused = document.activeElement
    const focusWasOnAnotherTab =
      focused instanceof HTMLElement &&
      focused.getAttribute('role') === 'tab' &&
      focused !== ref.current
    if (focusWasOnAnotherTab) ref.current?.focus()
  }, [isActive])

  // The tablist is ONE tab stop; the arrows move within it.
  function handleKeyDown(event: React.KeyboardEvent<HTMLButtonElement>) {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
    event.preventDefault()
    const step = event.key === 'ArrowRight' ? 1 : -1
    // Wraps, per the APG pattern: the ends of a tablist are not walls.
    onSelect(TABS[(TABS.indexOf(id) + step + TABS.length) % TABS.length])
  }

  return (
    <button
      ref={ref}
      type="button"
      role="tab"
      id={`history-tab-${id}`}
      aria-selected={isActive}
      aria-controls={`history-panel-${id}`}
      tabIndex={isActive ? 0 : -1}
      className="history-tab"
      data-testid={`history-tab-${id}`}
      onClick={() => onSelect(id)}
      onKeyDown={handleKeyDown}
    >
      {label}
    </button>
  )
}
