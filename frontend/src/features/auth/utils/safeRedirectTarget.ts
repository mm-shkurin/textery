// Where to land after a successful sign-in. The gate that bounced the user to /login puts the
// page they wanted in router state; only an in-app absolute path is honoured — taking a redirect
// target from anything a caller controls is how open-redirect bugs get in, and `state` is
// reachable from a crafted link. Split out of LoginForm so the component stays under the 200-line
// cap and the validation has one testable home.
export function safeRedirectTarget(from: unknown): string {
  if (typeof from === 'string' && from.startsWith('/') && !from.startsWith('//')) {
    return from
  }
  return '/'
}
