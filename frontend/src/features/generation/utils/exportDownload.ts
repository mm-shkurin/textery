import { browserDocument } from '../../../shared/lib/browser'

// Scenario 5.1: a successful export resolves a Blob that must reach the browser as a downloaded
// file. The standard idiom: mint an object URL for the blob, drive a DOM-connected anchor's click
// (a connected anchor is required for a real Firefox download), then release the URL so repeated
// exports do not leak blob URLs. Revoke is synchronous right after the click — the resolved blob
// is fully captured by the object URL before click(), so the eager release is safe here; the
// selenium 5.1 real-browser test is the backstop.
export function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const doc = browserDocument()
  if (!doc) return
  const anchor = doc.createElement('a')
  anchor.href = url
  anchor.download = filename
  doc.body.appendChild(anchor)
  anchor.click()
  doc.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}
