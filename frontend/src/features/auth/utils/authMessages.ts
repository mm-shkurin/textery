// Client-owned user-facing strings for the auth flows (login, registration, verification).
//
// Deliberately NOT declared in the api modules: every auth form test does
// `vi.mock('../../api/loginApi', () => ({ login: vi.fn() }))`, and that factory replaces
// the WHOLE module — a constant exported from there would arrive at the form as
// `undefined` under test while looking correct in production. Living in `utils/`, which
// no test mocks, keeps the value the tests assert against and the value the form renders
// the same object. `utils/` is also where `passwordPolicy.ts` already keeps shared
// auth strings.
//
// Each constant is the fallback for ONE meaning. They are not interchangeable: stamping the
// login constant onto a registration failure forges provenance a consumer cannot recover.
export const GENERIC_LOGIN_FAILURE_MESSAGE = 'Не удалось войти'
export const GENERIC_REGISTER_FAILURE_MESSAGE = 'Не удалось зарегистрироваться'
export const GENERIC_VERIFY_FAILURE_MESSAGE = 'Не удалось подтвердить код'

// The single definition of "this value can be shown to the user", shared by the form's
// render guard and by loginApi's normalizer so the two layers cannot drift into two
// different notions of usable — which is exactly what would happen if the constant's
// neighbours each kept their own inline check: every LoginForm test file mocks the api
// module wholesale, so an api-side fix earns no component-test credit and the two rules
// would diverge unobserved.
//
// The predicate is POSITIVE — "contains at least one non-whitespace character" — rather
// than a list of unusable values, because every attempt to enumerate the unusable ones has
// landed one character class short: first `''` (caught by truthiness), then `'   '` (truthy,
// so it cleared the truthiness fix and rendered a blank box).
//
// HONEST SCOPE, verified in Node rather than assumed — `/\S/` is NOT stronger than
// `.trim()`, it is equivalent. `\S` means "outside the ECMAScript WhiteSpace set", and the
// zero-width characters are outside it too, so ZWSP (U+200B), the word joiner (U+2060) and
// the LRM (U+200E) all TEST TRUE here, exactly as they survive trimming. A message of only
// zero-width characters still renders a blank box. `/\S/` was chosen for being a direct
// statement of the property wanted, and for closing the whitespace hole this scenario's
// test names — not because it closes the zero-width one. It does not. If that gap is worth
// covering, it needs its own red test and an explicit exclusion of the zero-width
// codepoints; do not assume this line already handles it.
//
// Takes `unknown`: `LoginApiError.message` is an unenforced compile-time type over parsed
// JSON, so a non-string (object, array, number) can reach both call sites at run time. The
// type guard narrows to `string`, which lets callers keep the declared type honestly rather
// than asserting it with `as string`.
export function isUsableMessage(message: unknown): message is string {
  return typeof message === 'string' && /\S/.test(message)
}
