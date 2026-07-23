// The single source of truth for which OAuth providers this client speaks. OAuthProviderButtons
// renders one control per entry, and the /auth/callback interstitial rejects any provider that is
// not exactly one of these — so adding a provider (or removing one) is a ONE-place edit here, and
// the callback's malformed-guard and the rendered buttons can never drift out of agreement.
export const OAUTH_PROVIDERS = [
  { provider: 'vk', label: 'Войти через VK ID', badge: 'VK', startPath: '/api/v1/auth/oauth/vk/start' },
  { provider: 'yandex', label: 'Войти через Yandex ID', badge: 'Я', startPath: '/api/v1/auth/oauth/yandex/start' },
] as const

// The valid provider identifiers as a lookup set, derived from OAUTH_PROVIDERS so it cannot drift.
const VALID_OAUTH_PROVIDERS = new Set<string>(OAUTH_PROVIDERS.map((p) => p.provider))

export function isValidOAuthProvider(provider: string | null): boolean {
  return provider !== null && VALID_OAUTH_PROVIDERS.has(provider)
}

// Client-side sanity cap on the one-time handoff code. A code longer than this is not a plausible
// provider grant — it is a probe or a corrupted URL — so the callback refuses to spend it. The cap
// is INCLUSIVE: a code of exactly OAUTH_CODE_MAX_LENGTH chars is valid; the first invalid length is
// one over (strict `>`), NOT `>=`.
export const OAUTH_CODE_MAX_LENGTH = 512

// Pure pre-exchange validation for the /auth/callback screen. A callback is malformed when the
// provider is not one we speak, OR the code is blank (empty or whitespace-only — `/\S/` mirrors the
// isUsableMessage convention), OR the code exceeds the sanity cap. Malformed callbacks resolve to
// the terminal error state without ever issuing an exchange.
export function isMalformedCallback(provider: string | null, code: string): boolean {
  if (!isValidOAuthProvider(provider)) return true
  if (!/\S/.test(code)) return true
  if (code.length > OAUTH_CODE_MAX_LENGTH) return true
  return false
}
