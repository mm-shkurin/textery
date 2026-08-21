// The four things the browser reports, and the guards that keep each of them counted ONCE.
//
// Every tracker here is `…Once` for the same reason: React StrictMode double-invokes effects in
// development and genuinely re-runs them, the router re-mounts a screen on every in-app
// navigation back to it, and a page load that reported two site visits doubles the denominator of
// every conversion rate in the product. The occurrence key already collapses a duplicate REQUEST
// server-side; these guards stop the duplicate from being a second occurrence in the first place.
//
// The keys live in module state, which is per page load — exactly the lifetime "once per visit"
// means. `SITE_VISITED` is once per load; `EDITOR_OPENED` is once per document, so opening a
// second document in the same session is a second opening and opening the same one twice in one
// gesture is not.
import { browserWindow } from '../lib/browser'
import { BROWSER_EVENTS, report } from './analyticsClient'
import { captureAttribution } from './attribution'

const reported = new Set<string>()

// Test-only reset. The guards are page-load-scoped by design, and a test file that renders the
// app twice is two page loads in every sense except this module's.
export function resetTrackers(): void {
  reported.clear()
}

// Called once, as early as the app can: it also freezes first-touch attribution, and the URL's
// campaign parameters are only reliably present before the router has had a chance to rewrite it.
export function trackSiteVisit(search: string = browserWindow()?.location.search ?? ''): void {
  captureAttribution(search)
  reportOnce('site-visit', BROWSER_EVENTS.siteVisited)
}

// The registration SCREEN was reached — the top of the funnel's second step. Reported on arrival
// rather than on submit, deliberately: the interesting number is how many people who saw the form
// finished it, which is unanswerable if the event only fires when they do.
export function trackRegistrationStarted(): void {
  reportOnce('registration-started', BROWSER_EVENTS.registrationStarted)
}

// A document was opened in the editor. Keyed on the document, so the funnel can tell "opened
// three documents" from "opened one and re-rendered three times".
export function trackEditorOpened(documentId: string): void {
  reportOnce(`editor-opened:${documentId}`, BROWSER_EVENTS.editorOpened)
}

function reportOnce(key: string, eventName: (typeof BROWSER_EVENTS)[keyof typeof BROWSER_EVENTS]) {
  if (reported.has(key)) return
  reported.add(key)
  report(eventName)
}
