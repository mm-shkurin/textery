// Client-owned user-facing strings for the login flow.
//
// Deliberately NOT declared in `loginApi.ts`: every LoginForm test file does
// `vi.mock('../../api/loginApi', () => ({ login: vi.fn() }))`, and that factory replaces
// the WHOLE module — a constant exported from there would arrive at the form as
// `undefined` under test while looking correct in production. Living in `utils/`, which
// no test mocks, keeps the value the tests assert against and the value the form renders
// the same object. `utils/` is also where `passwordPolicy.ts` already keeps shared
// auth strings.
export const GENERIC_LOGIN_FAILURE_MESSAGE = 'Не удалось войти'
