// Save-status vocabulary shared by EVERY ManualEditor suite that observes whether the document
// reads clean or dirty — autosave suites and plain-editor suites alike. It lives apart from
// ManualEditor.autosave.testSupport because most of its consumers (dirty, saveStatus, initError,
// beforeUnloadGuard, the base smoke test) have nothing to do with debounced autosave, and an
// autosave-named import in those files misstates what they depend on.

// The two save-status badge strings rendered by ManualEditorSaveStatus. They live as inline JSX
// literals in production (no exported constant to import), so this is the single place the test
// suite spells them — retyping them per file is how one suite ends up asserting a stale wording.
export const SAVED_STATUS = 'Сохранено'
export const DIRTY_STATUS = 'Черновик, ещё не сохранён'

// The modifier class each badge branch renders. Asserting the class alongside the text is what
// keeps a badge assertion from being tautological: `getByText(SAVED_STATUS).textContent` can only
// ever equal SAVED_STATUS — the query already matched on it — whereas the variant class is an
// independent fact about WHICH of ManualEditorSaveStatus's mutually exclusive branches rendered.
export const SAVE_STATUS_BASE_CLASS = 'me-save-status'
export const SAVED_BADGE_CLASS = 'me-save-status--saved'
export const DIRTY_BADGE_CLASS = 'me-save-status--dirty'
// The branch H9.4 demands and ManualEditorSaveStatus does not render yet: "a save attempt failed and
// is being retried". Declared here beside its three siblings rather than inside the one suite that
// asserts it, so the badge vocabulary stays in a single place — a per-suite copy of a modifier name
// is exactly how one suite ends up asserting a class GREEN later renamed.
export const RETRYING_BADGE_CLASS = 'me-save-status--retrying'

// The badge's stable root element, found by the base class every branch renders. Derived from
// SAVE_STATUS_BASE_CLASS rather than respelled as a literal '.me-save-status'.
export const SAVE_STATUS_BASE_SELECTOR = `.${SAVE_STATUS_BASE_CLASS}`

// The exact className a badge branch must carry: the base class plus exactly one modifier. Asserting
// against this instead of a bare toHaveClass is what makes a badge assertion prove EXCLUSIVITY —
// toHaveClass(RETRYING) still passes if the element also carries --dirty or --saved, which is the
// most likely way a GREEN bolts a new branch on beside the old one instead of replacing it.
export function badgeClassName(modifier: string): string {
  return `${SAVE_STATUS_BASE_CLASS} ${modifier}`
}

// The save-failure banner's test id. Like the badge strings above it exists only as an inline JSX
// literal in production, so the suite spells it once here instead of retyping it per assertion.
export const SAVE_ERROR_TESTID = 'me-save-error'

// Dispatches a cancelable beforeunload and reports whether the app's guard cancelled it — i.e.
// whether the browser would show its native "leave?" prompt. Shared by every suite that asserts
// the guard is armed or disarmed.
export function dispatchBeforeUnload(): boolean {
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  return event.defaultPrevented
}
