// Where a user goes the instant their account is verified, and how they get there signed in.
//
// Verification does not mint a session (see registrationHandoff for the probe), so this trades
// the remembered registration password for real tokens and reports where to send the user. It
// lives outside VerifyCodeForm because it is a decision with four outcomes, not a line of glue —
// and because the form is a form, not a place to keep auth policy.
import { login } from '../api/loginApi'
import { consumeRegistration } from './registrationHandoff'
import { saveSession } from './authSession'

export const LANDING_PATH = '/'
export const LOGIN_PATH = '/login'

// Never a thrown error: every outcome here is a place to send the user, and a verified account
// is good news in all four. The worst case is "sign in by hand", never "something went wrong".
export async function signInAfterVerification(email: string): Promise<string> {
  const password = consumeRegistration(email)
  if (!password) {
    // No handoff: the tab was reloaded, /verify was opened directly, or the code belongs to an
    // account registered elsewhere. Nothing is wrong — we simply cannot sign them in without a
    // password, and asking for one is the honest move.
    return LOGIN_PATH
  }

  try {
    const session = await login(email, password)
    // A 200 with no token is a broken contract, not a sign-in. Landing them on the landing page
    // "authenticated" with nothing to send would fail at the first request, somewhere that
    // cannot explain itself — the same reason LoginForm checks this.
    if (!session.accessToken || !saveSession(session)) {
      return LOGIN_PATH
    }
    return LANDING_PATH
  } catch {
    // The account IS verified — that already succeeded and is not undone by this. Only the
    // convenience of skipping the login screen is lost, so send them to it rather than
    // reporting a failure of the thing that worked.
    return LOGIN_PATH
  }
}
