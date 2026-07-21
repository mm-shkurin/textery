// Client-owned user-facing strings for the auth flows (login, registration, verification).
//
// NOT declared in the api modules: every auth form test replaces the whole api module with
// `vi.mock('../../api/loginApi', () => ({ login: vi.fn() }))`, so a constant exported from there
// reaches the form as `undefined` under test while looking correct in production. `utils/` is
// mocked by nothing, and is already where passwordPolicy.ts keeps shared auth copy.
//
// Each constant is the fallback for ONE meaning, and they are not interchangeable: stamping the
// login constant onto a registration failure forges provenance a consumer cannot recover.
export const GENERIC_LOGIN_FAILURE_MESSAGE = 'Не удалось войти'
// Network/transport failure copy — a connection problem, not a rejected credential. Kept DISTINCT
// from the generic login-failure text so the form can tell the user their password may be fine and
// to retry, rather than implying it was wrong. Form-owned (display seam): the api mapper never sees
// this, so a fixture carrying no network text still renders it.
export const NETWORK_LOGIN_FAILURE_MESSAGE =
  'Не удалось связаться с сервером. Проверьте подключение и попробуйте снова.'
export const GENERIC_REGISTER_FAILURE_MESSAGE = 'Не удалось зарегистрироваться'
export const GENERIC_VERIFY_FAILURE_MESSAGE = 'Не удалось подтвердить код'

// The single definition of "this value can be shown to the user", shared by the forms' render
// guards and the api normalizer so the two layers cannot drift — they would, unobserved, since
// the form tests mock the api module and an api-side fix earns no component-test credit.
//
// Positive predicate ("has a non-whitespace character") rather than a list of unusable values:
// enumerating those landed a class short twice — first `''`, then `'   '`, which is truthy and
// rendered a blank box.
//
// HONEST SCOPE: `/\S/` is equivalent to `.trim()`, not stronger. Zero-width characters (ZWSP
// U+200B, word joiner U+2060, LRM U+200E) are outside the WhiteSpace set, so they pass here and
// still render a blank box. Closing that needs its own test and an explicit exclusion — do not
// assume this line already does it.
//
// Takes `unknown` because `message` is an unenforced compile-time type over parsed JSON: a
// non-string can reach both call sites at run time. Narrowing lets callers keep the declared
// type honestly instead of asserting it with `as string`.
export function isUsableMessage(message: unknown): message is string {
  return typeof message === 'string' && /\S/.test(message)
}
