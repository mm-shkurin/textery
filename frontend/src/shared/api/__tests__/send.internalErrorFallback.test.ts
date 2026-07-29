import { describe, expect, it } from 'vitest'
import { describeFailure } from '../send'
import {
  ORIGIN_INTERNAL_ERROR_BODY,
  ORIGIN_PROVIDER_UNAVAILABLE_BODY,
} from './originErrorBodies'

// H9.4. `describeFailure` renders `body.detail ?? body.message` verbatim, and the origin's
// catch-all 500 body is measured, real, and ENGLISH: "An unexpected error occurred. Please try
// again." (`exception_handlers.py`, pinned in `originErrorBodies.ts`). So every render site in this
// Russian UI puts an English sentence on screen the moment anything 500s — and every suite that
// covered those sites hid it by inventing a Russian `message` no server ever sends.
//
// The decision: for `error_code === 'INTERNAL_ERROR'` the caller's Russian fallback wins and the
// body's text is ignored. NOT for 5xx generally — a backend that took the trouble to EXPLAIN a
// failure (a provider quota, a rejected document size) has put the explanation in that text and
// nowhere else, and swallowing it would trade one unreadable message for a useless one. The
// carve-out is keyed on the code that means "we have nothing to tell you".
const FALLBACK = 'Не удалось выполнить операцию'

describe('describeFailure — the origin catch-all 500 must not put English on a Russian screen', () => {
  // RED: describeFailure returns 'An unexpected error occurred. Please try again.' (the body's
  // own message) instead of `${FALLBACK} (HTTP 500)`. Un-skip in green-frontend.
  it.skip("replaces the catch-all 500's English text with the caller's fallback and the status", () => {
    expect(describeFailure({ status: 500, body: ORIGIN_INTERNAL_ERROR_BODY }, FALLBACK)).toBe(
      `${FALLBACK} (HTTP 500)`,
    )
  })

  // The guard against the carve-out widening into "never show server text on a 5xx". Same status
  // class, different code: this message is the only place its reason exists.
  it('still renders the server text for a 5xx that is not the catch-all', () => {
    expect(describeFailure({ status: 503, body: ORIGIN_PROVIDER_UNAVAILABLE_BODY }, FALLBACK)).toBe(
      ORIGIN_PROVIDER_UNAVAILABLE_BODY.message,
    )
  })

  // Keyed on the code AND the status class, not the code alone. A 4xx is a decided answer whose
  // text is addressed to the user; nothing about this scenario changes it.
  it('leaves 4xx text alone even when it carries the catch-all code', () => {
    expect(
      describeFailure({ status: 400, body: { error_code: 'INTERNAL_ERROR', detail: 'Тема пуста' } }, FALLBACK),
    ).toBe('Тема пуста')
  })

  // A 500 with no code at all is not the catch-all shape and keeps its text — the branch must read
  // `error_code`, not "any 500 with a message".
  it('still renders the server text for a codeless 500', () => {
    expect(describeFailure({ status: 500, body: { message: 'Хранилище недоступно' } }, FALLBACK)).toBe(
      'Хранилище недоступно',
    )
  })
})
