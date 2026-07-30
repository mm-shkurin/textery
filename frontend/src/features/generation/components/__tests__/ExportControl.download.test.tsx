import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { ExportControl } from '../ExportControl'

// exportDocument is the only runtime import ExportControl pulls from documentApi; an ES module
// namespace is frozen, so the mock must be declared via an explicit factory.
vi.mock('../../api/documentApi', () => ({
  exportDocument: vi.fn(),
}))

// jsdom implements neither URL.createObjectURL nor URL.revokeObjectURL, so we install our own
// stubs and assert against them. The stub returns a fixed sentinel URL so the revoke assertion can
// prove the SAME url produced by createObjectURL is the one handed to revokeObjectURL.
const OBJECT_URL = 'blob:mock-object-url'

// Scenario 5.1: a successful export must deliver the resolved Blob to the browser as a downloaded
// file. Today ExportControl awaits exportDocument and DISCARDS the blob — no object URL, no anchor,
// no click — so a successful export downloads nothing. These pin the blob→download contract:
//   1. URL.createObjectURL is called with the EXACT resolved Blob.
//   2. a download fires via an anchor whose `download` attr is a format-derived filename
//      (…​.pdf for pdf, …​.docx for docx) — proving the extension is not hardcoded.
//   3. the created object URL is revoked after use so repeated exports do not leak blob URLs.
describe('ExportControl download delivery on successful export', () => {
  let createObjectURL: ReturnType<typeof vi.fn>
  let revokeObjectURL: ReturnType<typeof vi.fn>
  let clickedDownloads: string[]

  beforeEach(() => {
    vi.clearAllMocks()
    createObjectURL = vi.fn(() => OBJECT_URL)
    revokeObjectURL = vi.fn()
    URL.createObjectURL = createObjectURL as unknown as typeof URL.createObjectURL
    URL.revokeObjectURL = revokeObjectURL as unknown as typeof URL.revokeObjectURL
    // Capture the `download` attribute of every anchor whose click() fires, without navigating.
    clickedDownloads = []
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clickedDownloads.push(this.getAttribute('download') ?? '')
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function triggerExport(format: 'pdf' | 'docx') {
    fireEvent.click(screen.getByTestId('export-control-trigger'))
    fireEvent.click(screen.getByTestId(`export-option-${format}`))
  }

  // RED 5.1: FAILS on current code — ExportControl awaits exportDocument and discards the resolved
  // blob, so URL.createObjectURL is never called (got 0 calls, expected 1) and no download fires.
  // green-frontend 5.1 adds the blob→object-URL→anchor-click→revoke delivery.
  it('hands the exact resolved Blob to createObjectURL and downloads it, then revokes the url', async () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' })
    vi.mocked(documentApi.exportDocument).mockResolvedValue(blob)

    render(<ExportControl documentId="doc-1" />)
    triggerExport('pdf')

    // The blob the transport resolved — not a fresh one — is what becomes the download source.
    await waitFor(() => expect(createObjectURL).toHaveBeenCalledTimes(1))
    expect(createObjectURL).toHaveBeenCalledWith(blob)

    // A download actually fired, carrying a .pdf filename derived from the export format.
    expect(clickedDownloads).toHaveLength(1)
    expect(clickedDownloads[0].endsWith('.pdf')).toBe(true)

    // The object URL is released after use, on the SAME url createObjectURL minted.
    expect(revokeObjectURL).toHaveBeenCalledWith(OBJECT_URL)
  })

  // RED 5.1: FAILS on current code — no anchor is created or clicked, so clickedDownloads stays []
  // (expected length 1). green-frontend 5.1 must derive the filename extension from the format.
  it('derives a .docx filename when exporting docx, proving the extension is format-driven', async () => {
    const blob = new Blob(['PK'], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    vi.mocked(documentApi.exportDocument).mockResolvedValue(blob)

    render(<ExportControl documentId="doc-1" />)
    triggerExport('docx')

    await waitFor(() => expect(clickedDownloads).toHaveLength(1))
    expect(clickedDownloads[0].endsWith('.docx')).toBe(true)
  })

  // RED 5.1: passes vacuously today (no download path exists at all); skipped so the whole new
  // suite activates together in green, where it becomes a real guard that the reject path mints no
  // object URL and fires no download.
  it('triggers no download when the export fails', async () => {
    vi.mocked(documentApi.exportDocument).mockRejectedValue(new Error('boom'))

    render(<ExportControl documentId="doc-1" />)
    triggerExport('pdf')

    // The rejection path must never mint an object URL or fire a download.
    await screen.findByTestId('export-error')
    expect(createObjectURL).not.toHaveBeenCalled()
    expect(clickedDownloads).toHaveLength(0)
  })
})
