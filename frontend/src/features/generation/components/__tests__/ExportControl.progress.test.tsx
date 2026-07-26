import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fireEvent,
  render,
  screen,
  waitForElementToBeRemoved,
} from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { ExportControl } from '../ExportControl'

// exportDocument is the only runtime import ExportControl pulls from documentApi; an ES module
// namespace is frozen, so the mock must be declared via an explicit factory.
vi.mock('../../api/documentApi', () => ({
  exportDocument: vi.fn(),
}))

// RED 2026-07-26 (scenario 3.1): ExportControl has an isExporting in-flight lock but renders no
// visible indicator yet. green-frontend adds an element with data-testid="export-spinner" mounted
// while isExporting is true. Remove .skip in green-frontend once the spinner is implemented.
describe.skip('ExportControl in-flight progress indicator', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows no exporting indicator before an export is triggered', () => {
    vi.mocked(documentApi.exportDocument).mockReturnValue(new Promise(() => {}))

    render(<ExportControl documentId="doc-1" />)

    // Idle: nothing has been dispatched, so the spinner must be absent from the DOM entirely.
    expect(screen.queryByTestId('export-spinner')).toBeNull()
  })

  it('shows the exporting indicator while the export is in flight', () => {
    // A promise that never settles keeps the export in flight for the whole test, so the
    // spinner's presence can only come from the in-flight state, not a settled request.
    vi.mocked(documentApi.exportDocument).mockReturnValue(new Promise(() => {}))

    render(<ExportControl documentId="doc-1" />)
    fireEvent.click(screen.getByTestId('export-control-trigger'))
    fireEvent.click(screen.getByTestId('export-option-pdf'))

    expect(screen.getByTestId('export-spinner')).toBeVisible()
  })

  it('removes the exporting indicator after the export settles', async () => {
    // A manually-resolvable deferred: the spinner rises on click and must fall again once the
    // request resolves, so both edges are asserted deterministically (no timing races).
    let resolveExport: (value: Blob) => void = () => {}
    const deferred = new Promise<Blob>((resolve) => {
      resolveExport = resolve
    })
    vi.mocked(documentApi.exportDocument).mockReturnValue(deferred)

    render(<ExportControl documentId="doc-1" />)
    fireEvent.click(screen.getByTestId('export-control-trigger'))
    fireEvent.click(screen.getByTestId('export-option-pdf'))

    // Rising edge holds while unresolved.
    expect(screen.getByTestId('export-spinner')).toBeVisible()

    resolveExport(new Blob())
    // Falling edge: once the success path settles, the indicator is removed again.
    await waitForElementToBeRemoved(() => screen.queryByTestId('export-spinner'))
    expect(screen.queryByTestId('export-spinner')).toBeNull()
  })
})
