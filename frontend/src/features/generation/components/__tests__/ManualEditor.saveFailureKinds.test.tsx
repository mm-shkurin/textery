import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { SessionExpiredError } from '../../../auth/api/authorizedRequest'
import { VersionConflictError } from '../../../../shared/api/send'
import { CONFLICT_ERROR_MESSAGE, SAVE_ERROR_MESSAGE } from '../../hooks/useDocumentSave'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// A failed save is not one thing, and the banner must not pretend it is. Two of these three
// rejections are NOT connection problems, and the default copy ("Проверьте соединение… текст
// сохранён локально в редакторе") is both wrong about the cause and — for the conflict — a
// promise that cannot be kept.
describe('ManualEditor — what a failed save says depends on why it failed', () => {
  beforeEach(() => {
    // The banner is the assertion; the console.error beside it is the only diagnostic this app
    // has and would otherwise print a real-looking failure into a passing run.
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
  })

  async function saveRejectingWith(error: unknown) {
    await renderEditorWithDocumentCreated()
    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)
    vi.mocked(documentApi.saveDocument).mockRejectedValue(error)

    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))

    return await screen.findByTestId('me-save-error')
  }

  it('blames the connection only when the failure actually is one', async () => {
    expect(await saveRejectingWith(new Error('network down'))).toHaveTextContent(SAVE_ERROR_MESSAGE)
  })

  // authorizedRequest raises this so callers can tell "you are signed out" from "your document
  // could not be saved". Flattened into the default, it told a signed-out user their connection
  // was at fault, reassured them the text was safe, and invited them to retry a button that
  // cannot work until they sign in.
  it('says the session expired, not that the connection failed', async () => {
    const banner = await saveRejectingWith(new SessionExpiredError())

    expect(banner).toHaveTextContent('Сессия истекла. Войдите снова.')
    expect(banner).not.toHaveTextContent('Проверьте соединение')
  })

  // saveDocument already answers the FIRST 409 by refetching the version and retrying, so a
  // conflict arriving at the banner has survived that: another writer landed during the retry.
  // Nothing about that is a connection, and the text in the editor is genuinely not saved.
  it('says the document was changed elsewhere, and does not promise the text is safe', async () => {
    const banner = await saveRejectingWith(new VersionConflictError())

    expect(banner).toHaveTextContent(CONFLICT_ERROR_MESSAGE)
    expect(banner).not.toHaveTextContent('Проверьте соединение')
    // The trap this pins: the default copy's "текст сохранён локально в редакторе" is a promise
    // the conflict branch cannot keep, and a user who believes it loses the paragraph.
    expect(banner).not.toHaveTextContent('текст сохранён локально в редакторе')
  })
})
