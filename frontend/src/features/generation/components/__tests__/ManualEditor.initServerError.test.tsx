import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// The init half of the H9.4 `send` carve-out. `send` now rethrows 5xx as a bare `HttpError`
// OBJECT so the autosave retry policy can read `.status` — and an `HttpError` is NOT an `Error`
// (httpClient.ts:141), so every `error instanceof Error ? error.message : FALLBACK` downstream
// silently collapsed to the generic string on exactly the failures worth reporting. That is the
// fixture divergence the carve-out fixed at the SAVE seam and would otherwise have recreated
// verbatim here.
//
// Deliberately NO `vi.mock('../../api/documentApi')`: its sibling `ManualEditor.initError.test.tsx`
// mocks the module and hand-rolls `new Error('… (HTTP 500)')` — a shape `send` no longer emits —
// so it stays green no matter what this seam does. Nothing but a real `fetch` → `httpClient` →
// `send` → `documentApi` → hook chain can tell whether the server's text still reaches a person.
describe('ManualEditor init server errors reach the user through the real send chain', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  function stubServerError(body: Record<string, unknown>): void {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status: 500 }))),
    )
  }

  // The origin's real catch-all body (`exception_handlers.py:63-77`). Its `message` is the whole
  // reason the body is carried across the boundary at all.
  it('shows the origin message when creating the document 500s', async () => {
    stubServerError({ error_code: 'INTERNAL_ERROR', message: 'Внутренняя ошибка сервера' })

    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)

    expect(await screen.findByTestId('me-init-error')).toHaveTextContent(
      'Внутренняя ошибка сервера',
    )
  })

  // A proxy's 502/500 HTML page: `res.json()` throws and `performRequest` substitutes `{}`, so
  // there is no message and the STATUS is the only fact left. It must still survive to the screen
  // — dropping it is the difference between a report a person can act on and "что-то пошло не так".
  it('keeps the status visible when the 500 body carries no readable text', async () => {
    stubServerError({})

    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)

    expect(await screen.findByTestId('me-init-error')).toHaveTextContent('(HTTP 500)')
  })

  // getDocument is the second non-save `send` caller in this feature and takes a different catch.
  it('shows the origin message when loading an existing document 500s', async () => {
    stubServerError({ error_code: 'INTERNAL_ERROR', message: 'Документ временно недоступен' })

    render(
      <ManualEditor
        documentType="doklad"
        documentTypeLabel="Доклад"
        onBack={vi.fn()}
        existingDocumentId="doc-9"
      />,
    )

    expect(await screen.findByTestId('me-init-error')).toHaveTextContent(
      'Документ временно недоступен',
    )
  })
})
