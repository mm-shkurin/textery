// HTTP client for the login API (POST authenticate).
// RED-phase import scaffolding only — no implementation yet (Scenario 5.2).
export interface LoginResult {
  accessToken: string
  refreshToken: string
}

export interface LoginApiError {
  errorCode: string
  message: string
}

export async function login(email: string, password: string): Promise<LoginResult> {
  void email
  void password
  throw new Error('Not implemented')
}
