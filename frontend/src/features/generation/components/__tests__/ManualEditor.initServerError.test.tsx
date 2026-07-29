import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import { CREATE_FAILED_MESSAGE, LOAD_FAILED_MESSAGE } from '../../hooks/useDocumentInit'
import {
  ORIGIN_INTERNAL_ERROR_BODY,
  ORIGIN_PROVIDER_UNAVAILABLE_BODY,
} from '../../../../shared/api/__tests__/originErrorBodies'
import {
  ACCESS_TOKEN,
  authorizationHeaders,
  requestLog,
  resetOriginStubs,
  seedSession,
  stubOriginError,
} from '../../../../shared/api/__tests__/originStubs'

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
const EXISTING_DOCUMENT_ID = 'doc-9'
const CREATE_REQUEST = 'POST /api/v1/documents'
const LOAD_REQUEST = `GET /api/v1/documents/${EXISTING_DOCUMENT_ID}`

// What the screen and the wire both say, as ONE value. The banner text alone cannot tell "the
// origin refused" from "the request never went out" — both reach the same catch and render the
// same fallback — so the request log and the header travel with it.
interface Observed {
  bannerText: string
  requests: string[]
  authorizationHeaders: string[]
}

describe('ManualEditor init server errors reach the user through the real send chain', () => {
  beforeEach(seedSession)
  afterEach(resetOriginStubs)

  // No assertion in here: every failure is attributable to the `it` that made the claim.
  async function renderAndFail(
    body: Record<string, unknown>,
    existingDocumentId?: string,
  ): Promise<Observed> {
    const fetchMock = stubOriginError(body)
    render(
      <ManualEditor
        documentType="doklad"
        documentTypeLabel="Доклад"
        onBack={vi.fn()}
        existingDocumentId={existingDocumentId}
      />,
    )
    const banner = await screen.findByTestId('me-init-error')
    return {
      bannerText: banner.textContent ?? '',
      requests: requestLog(fetchMock),
      authorizationHeaders: authorizationHeaders(fetchMock),
    }
  }

  // Exact text, not `toHaveTextContent`'s substring: the whole point of these cases is WHICH of two
  // strings is on screen, and a substring match cannot tell "the fallback replaced the English"
  // from "the fallback was concatenated in front of it". The request pins that exactly one call
  // went out, carrying the seeded session — so the 500 is the origin refusing, not the transport
  // declining to send and not a 401 replay.
  function expectShowed(observed: Observed, bannerText: string, request: string): void {
    expect(observed).toEqual({
      bannerText,
      requests: [request],
      authorizationHeaders: [`Bearer ${ACCESS_TOKEN}`],
    })
  }

  // H9.4: the origin's catch-all 500 is measured and ENGLISH, so its `message` must NOT reach this
  // Russian screen — the caller's own fallback plus the status does. `useDocumentInit.ts:91`.
  //
  // This case exists because the one below it was, until now, stubbing an INTERNAL_ERROR 500 with a
  // hand-rolled RUSSIAN message. That fixture made "the origin's text reaches the user" look like a
  // proven good outcome while the live origin was putting an English sentence in front of a user.
  // RED: the banner shows 'An unexpected error occurred. Please try again.' instead of
  // CREATE_FAILED_MESSAGE + ' (HTTP 500)'. Un-skip in green-frontend.
  it.skip("does not put the catch-all 500's English text on screen when creating the document", async () => {
    const observed = await renderAndFail(ORIGIN_INTERNAL_ERROR_BODY)
    expectShowed(observed, `${CREATE_FAILED_MESSAGE} (HTTP 500)`, CREATE_REQUEST)
  })

  // The same for the LOAD half — a second catch (`useDocumentInit.ts:76`) with its own fallback, so
  // a fix applied to only one of them is visible here.
  // RED: the banner shows 'An unexpected error occurred. Please try again.' instead of
  // LOAD_FAILED_MESSAGE + ' (HTTP 500)'. Un-skip in green-frontend.
  it.skip("does not put the catch-all 500's English text on screen when loading a document", async () => {
    const observed = await renderAndFail(ORIGIN_INTERNAL_ERROR_BODY, EXISTING_DOCUMENT_ID)
    expectShowed(observed, `${LOAD_FAILED_MESSAGE} (HTTP 500)`, LOAD_REQUEST)
  })

  // A 5xx the backend deliberately EXPLAINED still reaches the user verbatim — the carve-out above
  // is keyed on the catch-all code, not on the status class. Re-pointed from a hand-rolled
  // `INTERNAL_ERROR` + Russian body, which is a shape no server sends.
  it('shows the origin message when creating the document fails with an explained 5xx', async () => {
    const observed = await renderAndFail(ORIGIN_PROVIDER_UNAVAILABLE_BODY)
    expectShowed(observed, ORIGIN_PROVIDER_UNAVAILABLE_BODY.message, CREATE_REQUEST)
  })

  // A proxy's 502/500 HTML page: `res.json()` throws and `performRequest` substitutes `{}`, so
  // there is no message and the STATUS is the only fact left. It must still survive to the screen
  // — dropping it is the difference between a report a person can act on and "что-то пошло не так".
  it('keeps the status visible when the 500 body carries no readable text', async () => {
    const observed = await renderAndFail({})
    expectShowed(observed, `${CREATE_FAILED_MESSAGE} (HTTP 500)`, CREATE_REQUEST)
  })

  // getDocument is the second non-save `send` caller in this feature and takes a different catch.
  // Explained 5xx, for the same reason as the create case above.
  it('shows the origin message when loading an existing document hits an explained 5xx', async () => {
    const observed = await renderAndFail(ORIGIN_PROVIDER_UNAVAILABLE_BODY, EXISTING_DOCUMENT_ID)
    expectShowed(observed, ORIGIN_PROVIDER_UNAVAILABLE_BODY.message, LOAD_REQUEST)
  })
})
