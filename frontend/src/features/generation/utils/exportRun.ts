import { exportDocument, type ExportFormat } from '../api/documentApi'
import { triggerBrowserDownload } from '../utils/exportDownload'

// What the saved file is called before its extension. A literal `document.${format}` inside the
// template read as a property access on the DOM global to every reader and every scanner.
const EXPORT_BASENAME = 'document'

// Scenario 4.1: on a dirty editor, persist first and dispatch only after save resolves so the
// export never ships stale stored html.
//
// Awaits ONLY a promise-returning save so the export waits for persistence to settle (Scenario
// 4.1's pinned ordering). A fire-and-forget save that returns void is kicked off and not awaited —
// awaiting `undefined` would add nothing and would needlessly defer the dispatch a microtask.
//
// Returns false when the save FAILED: the export is skipped (never ship a stale file) AND the
// caller must not raise the generic export banner. useDocumentSave already surfaced the accurate
// data-loss message (SessionExpired / VersionConflict) in ManualEditor's save-error banner; the
// generic "Не удалось экспортировать" would only mask it.
async function persisted(save: () => void | Promise<void>): Promise<boolean> {
  const saving = save()
  if (!saving || typeof saving.then !== 'function') return true
  try {
    await saving
    return true
  } catch {
    return false
  }
}

// Resolves true when a file was delivered, false when a failed save skipped the export, and
// REJECTS when the export itself failed — which is the one case that earns the banner.
export async function runExport(
  documentId: string,
  format: ExportFormat,
  save?: () => void | Promise<void>,
): Promise<boolean> {
  if (save && !(await persisted(save))) return false
  const blob = await exportDocument(documentId, format)
  // Deliver the resolved blob to the browser as a download. The extension is derived from the
  // export format (….pdf / ….docx), never hardcoded, so a docx export ships a .docx file.
  triggerBrowserDownload(blob, `${EXPORT_BASENAME}.${format}`)
  return true
}
