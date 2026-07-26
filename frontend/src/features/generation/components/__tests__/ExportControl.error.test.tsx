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

// The exact message the transport rejects with (documentApi.exportDocument passes this string to
// `send` as the user-facing failure text). The inline error must surface this verbatim, not a
// generic substitute, so a transport wording change is caught here.
const EXPORT_ERROR_TEXT = 'Не удалось экспортировать документ'

// A manually-settleable deferred so each test controls resolve-vs-reject timing (mirrors 3.1).
function createDeferred() {
  let resolve: (value: Blob) => void = () => {}
  let reject: (reason: Error) => void = () => {}
  const promise = new Promise<Blob>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function triggerExport() {
  fireEvent.click(screen.getByTestId('export-control-trigger'))
  fireEvent.click(screen.getByTestId('export-option-pdf'))
}

describe('ExportControl export failure surfacing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows no inline error before an export is triggered', () => {
    vi.mocked(documentApi.exportDocument).mockReturnValue(new Promise(() => {}))

    render(<ExportControl documentId="doc-1" />)

    // Idle: nothing has failed, so no error and no retry may exist in the DOM.
    expect(screen.queryByTestId('export-error')).toBeNull()
    expect(screen.queryByTestId('export-retry')).toBeNull()
  })

  it('shows no inline error on the success path', async () => {
    const deferred = createDeferred()
    vi.mocked(documentApi.exportDocument).mockReturnValue(deferred.promise)

    render(<ExportControl documentId="doc-1" />)
    triggerExport()
    // Falling edge of the spinner marks the settle; the success path must leave no error behind.
    deferred.resolve(new Blob())
    await waitForElementToBeRemoved(() => screen.queryByTestId('export-spinner'))

    expect(screen.queryByTestId('export-error')).toBeNull()
  })

  it('surfaces an inline error with the transport message when the export rejects', async () => {
    const deferred = createDeferred()
    vi.mocked(documentApi.exportDocument).mockReturnValue(deferred.promise)

    render(<ExportControl documentId="doc-1" />)
    triggerExport()
    deferred.reject(new Error(EXPORT_ERROR_TEXT))

    // Rising edge: the rejection becomes a visible inline error carrying the exact wording.
    const error = await screen.findByTestId('export-error')
    expect(error).toBeVisible()
    expect(error).toHaveTextContent(EXPORT_ERROR_TEXT)
  })

  it('offers a retry control labelled "Повторить" alongside the error', async () => {
    const deferred = createDeferred()
    vi.mocked(documentApi.exportDocument).mockReturnValue(deferred.promise)

    render(<ExportControl documentId="doc-1" />)
    triggerExport()
    deferred.reject(new Error(EXPORT_ERROR_TEXT))

    const retry = await screen.findByTestId('export-retry')
    expect(retry).toBeVisible()
    expect(retry).toHaveAccessibleName('Повторить')
  })

  it('re-dispatches the export and clears the error when retry succeeds', async () => {
    const failed = createDeferred()
    const retried = createDeferred()
    vi.mocked(documentApi.exportDocument)
      .mockReturnValueOnce(failed.promise)
      .mockReturnValueOnce(retried.promise)

    render(<ExportControl documentId="doc-1" />)
    triggerExport()
    failed.reject(new Error(EXPORT_ERROR_TEXT))
    await screen.findByTestId('export-error')

    fireEvent.click(screen.getByTestId('export-retry'))

    // Retry is a genuine second dispatch carrying the same id and format, not decoration.
    expect(documentApi.exportDocument).toHaveBeenCalledTimes(2)
    expect(documentApi.exportDocument).toHaveBeenNthCalledWith(2, 'doc-1', 'pdf')

    // On the retry's success the inline error is removed.
    retried.resolve(new Blob())
    await waitForElementToBeRemoved(() => screen.queryByTestId('export-error'))
    expect(screen.queryByTestId('export-error')).toBeNull()
  })
})
