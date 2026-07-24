// Where to land after a successful sign-in. The gate that bounced the user to /login puts the
// page they wanted in router state; only an in-app absolute path is honoured — taking a redirect
// target from anything a caller controls is how open-redirect bugs get in, and `state` is
// reachable from a crafted link. Split out of LoginForm so the component stays under the 200-line
// cap and the validation has one testable home.
// The rejected shapes, and why each one is not just `//`:
//   //evil.com    — protocol-relative; the browser reads it as an absolute URL.
//   /\evil.com    — browsers NORMALISE a backslash to a forward slash in the authority position,
//                   so this is the same protocol-relative URL wearing a different character. A
//                   `startsWith('//')` check alone passes it straight through.
//   /\/evil.com, //\evil.com — the mixed forms of the same trick.
// Hence the test is on the SECOND character being any slash, not on the literal '//' prefix. A
// backslash anywhere else is rejected too: no in-app route contains one, so there is nothing to
// lose by refusing it and no need to reason about where else a browser might normalise it.
//
// React Router's `navigate()` happens to contain these today. That is not the guard — this is;
// relying on the router's normalisation would make an open redirect one dependency bump away.
function isInAppPath(from: string): boolean {
  return from.startsWith('/') && !/^[/\\]/.test(from.slice(1)) && !from.includes('\\')
}

export function safeRedirectTarget(from: unknown): string {
  if (typeof from === 'string' && isInAppPath(from)) {
    return from
  }
  return '/'
}
