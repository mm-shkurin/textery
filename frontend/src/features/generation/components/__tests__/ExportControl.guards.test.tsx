import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { ExportControl } from '../ExportControl'

// exportDocument is the only runtime import ExportControl pulls from documentApi; an ES module
// namespace is frozen, so the mock must be declared via an explicit factory (the auto-mock would
// also work, but naming the single symbol keeps the surface obvious).
vi.mock('../../api/documentApi', () => ({
  exportDocument: vi.fn(),
}))

describe('ExportControl early-return guards', () => {
  // Two tests share one module-level mock; clear call history so each asserts its own dispatches.
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not dispatch a second export while the first is still in flight', () => {
    // A promise that never settles keeps the lock engaged for the whole test, so any second
    // dispatch could only come from the in-flight guard being absent.
    vi.mocked(documentApi.exportDocument).mockReturnValue(new Promise(() => {}))

    render(<ExportControl documentId="doc-1" />)
    fireEvent.click(screen.getByTestId('export-control-trigger'))
    const pdfOption = screen.getByTestId('export-option-pdf')
    fireEvent.click(pdfOption)
    fireEvent.click(pdfOption)

    // Pin BOTH the guard (exactly one dispatch survives the double click) and the payload of
    // that single dispatch — the surviving call must carry the exact document id and format,
    // not merely "some" call.
    expect(documentApi.exportDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.exportDocument).toHaveBeenNthCalledWith(1, 'doc-1', 'pdf')
  })

  it('does not dispatch an export when there is no document id', () => {
    vi.mocked(documentApi.exportDocument).mockReturnValue(new Promise(() => {}))

    // Open the menu while a document exists, then lose the id (parent re-renders with null).
    // The menu stays mounted, so its options remain clickable — the only thing stopping a
    // dispatch is the missing-id guard inside the handler.
    const { rerender } = render(<ExportControl documentId="doc-1" />)
    fireEvent.click(screen.getByTestId('export-control-trigger'))
    rerender(<ExportControl documentId={null} />)
    fireEvent.click(screen.getByTestId('export-option-pdf'))

    expect(documentApi.exportDocument).toHaveBeenCalledTimes(0)
  })
})
