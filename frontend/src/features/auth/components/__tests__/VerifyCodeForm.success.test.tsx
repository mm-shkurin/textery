import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { VerifyCodeForm } from '../VerifyCodeForm'
import * as verifyApi from '../../api/verifyApi'
import * as postVerifySignIn from '../../utils/postVerifySignIn'

// Scenario 6.4 — a CORRECT code (verify resolves is_verified:true) signs the user in and takes
// them to the authenticated app shell, replacing history so Back does not return to /verify.
//
// BORN-GREEN regression guard (PASSES on current code). The success-navigation path
// (VerifyCodeForm handleSubmit L60-75: verify → setIsVerified → navigate(await
// signInAfterVerification(email), { replace: true })) already shipped in the out-of-TDD
// live-integration work — no production change is needed, so this pins the behavior against a
// future refactor rather than driving one. It also closes the 5.5 coverage gap flagged as "6.4
// territory": the setCodeError(false) at L62 on the resolved-is_verified:true path had NO
// happy-path vitest before this, because every prior verify test drives a rejection.
//
// signInAfterVerification owns the where/how-to-sign-in policy and is exhaustively unit-tested in
// utils/__tests__/postVerifySignIn.test.ts; here it is mocked to a known landing so this test pins
// only the component's contract: hand it the email, navigate to the target it returns, with
// { replace: true }.

const EMAIL = 'user@example.com'
// A distinctive sentinel, deliberately NOT '/'. signInAfterVerification really returns '/' on
// success, but it is mocked here — the test's job is to prove the component pipes whatever it
// returns into navigate. If the target were '/', a hardcoded navigate('/', …) that ignored the
// return value would pass this test; a sentinel makes the pipe the only way to pass.
const SIGN_IN_TARGET = '/post-verify-landing'

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../../api/verifyApi', async (importOriginal) => {
  const actual = await importOriginal<typeof verifyApi>()
  return { ...actual, verify: vi.fn() }
})

vi.mock('../../utils/postVerifySignIn', async (importOriginal) => {
  const actual = await importOriginal<typeof postVerifySignIn>()
  return { ...actual, signInAfterVerification: vi.fn() }
})

describe('VerifyCodeForm success navigation', () => {
  afterEach(() => {
    navigate.mockReset()
    vi.mocked(verifyApi.verify).mockReset()
    vi.mocked(postVerifySignIn.signInAfterVerification).mockReset()
  })

  it('signs the user in and replaces history with the authenticated app shell on a correct code', async () => {
    vi.mocked(verifyApi.verify).mockResolvedValue({ isVerified: true })
    vi.mocked(postVerifySignIn.signInAfterVerification).mockResolvedValue(SIGN_IN_TARGET)
    renderWithRouter(<VerifyCodeForm email={EMAIL} />)

    await act(async () => {
      fireEvent.click(screen.getByTestId('verify-confirm-button'))
    })

    // The sign-in step runs for THIS account — pins that the target is not a hardcoded '/', it is
    // whatever signInAfterVerification decides for this email.
    await waitFor(() =>
      expect(postVerifySignIn.signInAfterVerification).toHaveBeenCalledWith(EMAIL),
    )
    // The happy-path branch fully ran: setIsVerified(true) painted the success output, which also
    // pins that L62 setCodeError(false) executed on a resolved is_verified:true path (the 5.5 gap
    // this guard claims to close) rather than the line being merely incidentally covered.
    expect(screen.getByTestId('verify-success')).toBeInTheDocument()
    // The scenario's defining property: land on the app shell, replacing history so Back does not
    // walk back onto the just-confirmed /verify screen.
    expect(navigate).toHaveBeenCalledWith(SIGN_IN_TARGET, { replace: true })
  })
})
