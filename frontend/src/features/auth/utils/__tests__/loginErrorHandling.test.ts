import { describe, expect, it } from 'vitest'
import { isLoginNetworkError } from '../loginErrorHandling'

// The live backend's generic 500 is codeful — { error_code: 'INTERNAL_ERROR', message } — and
// toAuthApiError attaches `status` ONLY on the codeless path, so this shape reaches the classifier
// with an errorCode and no status. It is a server fault the user should be invited to retry, not a
// terminal business error. This is the fix target.
describe('isLoginNetworkError — server-fault INTERNAL_ERROR sentinel', () => {
  it('treats a codeful INTERNAL_ERROR 500 (no status) as a retryable network failure', () => {
    expect(isLoginNetworkError({ errorCode: 'INTERNAL_ERROR', message: 'oops' })).toBe(true)
  })
})

// Guard rails around the fix: pin the behavior the classifier ALREADY has so widening it for the
// sentinel does not regress the shapes that route correctly today.
describe('isLoginNetworkError — established bounds (born-green)', () => {
  it('keeps a status-bearing INTERNAL_ERROR 500 retryable via the status>=500 branch', () => {
    expect(
      isLoginNetworkError({ errorCode: 'INTERNAL_ERROR', message: 'oops', status: 500 }),
    ).toBe(true)
  })

  it('treats a bodyless transport error as network (no errorCode)', () => {
    expect(isLoginNetworkError(new TypeError('Failed to fetch'))).toBe(true)
  })

  it('treats a codeless 5xx gateway body as network', () => {
    expect(isLoginNetworkError({ errorCode: 'UNKNOWN_ERROR', message: '', status: 503 })).toBe(true)
  })

  it('keeps a 4xx business code (INVALID_CREDENTIALS) on the terminal/form-error path', () => {
    expect(isLoginNetworkError({ errorCode: 'INVALID_CREDENTIALS', message: 'bad' })).toBe(false)
  })

  it('keeps the expired-OAuth-code business error terminal', () => {
    expect(
      isLoginNetworkError({ errorCode: 'INVALID_OR_EXPIRED_OAUTH_CODE', message: 'expired' }),
    ).toBe(false)
  })
})
