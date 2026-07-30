import { useEffect } from 'react'

// Unsaved work lives only in Tiptap's in-memory state, so a tab-close or refresh drops it silently.
// beforeunload's native "leave?" prompt is the browser's one built-in defence, shown only when a
// listener calls preventDefault. Arm it while dirty, and detach on clean/unmount with the same
// handler reference so a closed editor cannot keep blocking navigation.
//
// Extracted from ManualEditor — which was near the 200-line limit and is otherwise pure wiring plus
// layout, every other concern already behind a hook (useDocumentSave, useAutosave, useDocumentInit).
//
// NOT features/auth's useUnsavedGuard: that one keeps its dirty state in an internal ref driven by
// markDirty/markClean and also prompts via window.confirm at react-router click seams. Here the
// dirty flag is already owned by the caller's render state, and there is no in-app link to guard —
// adopting that hook would mean both re-plumbing the flag and adding a confirm nobody asked for.
export function useBeforeUnloadGuard(hasUnsavedChanges: boolean) {
  useEffect(() => {
    if (!hasUnsavedChanges) return
    const guard = (event: BeforeUnloadEvent) => {
      // preventDefault marks the event cancelled on current Chromium, but legacy Chrome/Edge and
      // older Safari/Firefox only show the native "leave?" prompt when returnValue is also set —
      // without it the guard would arm yet display nothing on a subset of supported browsers.
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', guard)
    return () => window.removeEventListener('beforeunload', guard)
  }, [hasUnsavedChanges])
}
