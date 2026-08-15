// Which parts of src/ are allowed to import which, and the exceptions that are written down.
//
// README states the layering ("`auth` is not a neighbouring feature, it is the session layer;
// generation, history and documents sit on top of it, with no imports back"), and until now nothing
// enforced it. A prose rule about imports is a rule that holds until the first afternoon somebody
// needs a component from another feature and reaches for a `../../` — which is not a decision
// anyone makes deliberately, it is one made while looking at something else.
//
// The rule, in one line: a feature may import itself, `shared`, and the session layer. Anything
// else crossing a feature boundary has to be listed below, with a reason.

// The session layer. Not "a feature that is special": every screen needs a signed-in identity, so
// the alternative is duplicating token handling per feature, which is how two of them end up
// disagreeing about whether a session is still valid.
export const SESSION_LAYER = 'features/auth'

// `shared` importing a FEATURE is upside down by definition, and every one of these was still the
// right call at the time — which is exactly why they need naming rather than tolerating. A silent
// tolerance grows; a list gets read.
//
// All four are the same seam: something generic needs the signed-in identity. The real fix is a
// session module that does not live under `features/`, at which point every row here disappears.
export const ALLOWED_SHARED_TO_FEATURE = [
  {
    from: 'shared/api/send.ts',
    to: 'features/auth/api/authorizedRequest',
    why: 'send = transport + session + readable refusal; the session half is authorizedRequest, and httpClient must stay auth-free or the /auth/refresh client imports the client that refreshes it',
  },
  {
    from: 'shared/components/profile/ProfileAvatar.tsx',
    to: 'features/auth/utils/accountEmail',
    why: 'initials are derived from the identity by the same function the menu reads it with',
  },
  // Story 13 moved identity off the access token and onto `GET /api/v1/auth/me`. The snapshot has
  // to live in `shared/` — the header that reads it is a shared component on every authenticated
  // page, and `features/profile` is only ONE of its readers — but reaching that endpoint is a
  // session concern, so these three cross the same seam every row above does.
  {
    from: 'shared/identity/api/identityRequest.ts',
    to: 'features/auth/api/refreshApi',
    why: 'the identity read renews its own token on a 401 WITHOUT the session-ending clearSession authorizedRequest applies — that difference is the module',
  },
  {
    from: 'shared/identity/api/identityRequest.ts',
    to: 'features/auth/utils/authSession',
    why: 'it attaches the stored access token and persists a renewed one; the store is the session layer',
  },
  {
    from: 'shared/identity/api/profileApi.ts',
    to: 'features/auth/api/authorizedRequest',
    why: 'PATCH /me is user-initiated, so unlike the GET it goes through the session layer and may end a dead session',
  },
  {
    from: 'shared/identity/api/avatarApi.ts',
    to: 'features/auth/api/authorizedRequest',
    why: 'PUT/DELETE of the picture are user-initiated, so unlike the GET of its bytes they go through the session layer and may end a dead session',
  },
  {
    from: 'shared/identity/api/deleteAccountApi.ts',
    to: 'features/auth/api/authorizedRequest',
    why: 'deleting the account is the most user-initiated request there is, and it must travel the path where a dead session is reported as one',
  },
  {
    from: 'shared/identity/identityStore.ts',
    to: 'features/auth/utils/authSession',
    why: 'the identity snapshot is invalidated on every session change — signing in as somebody else keeps isAuthenticated true and changes only who you are',
  },
]

// The area an import path belongs to: a feature is `features/<name>`, everything else is its
// top-level directory. Deliberately coarse - this gate is about walls between features, and
// `components` vs `hooks` inside one feature is a different conversation.
export function areaOf(relativePath) {
  const parts = relativePath.split(/[\\/]/)
  return parts[0] === 'features' ? `features/${parts[1]}` : parts[0]
}

// Paths arrive with the platform's separator; every rule here is written with `/`. Comparing them
// unnormalised passes on Linux and fails on Windows, which is the worst shape a gate can have: a
// developer-only red that trains people to ignore it.
const slashed = (path) => path.split('\\').join('/')

export function isAllowed({ fromArea, toArea, fromFile, toPath }) {
  if (fromArea === toArea) return true
  if (toArea === 'shared') return true
  // `app` wires the screens together - importing every feature is its whole job. `main.tsx` is the
  // entry point and does one thing: mount `app`.
  if (fromArea === 'app' || fromArea === 'main.tsx') return true
  if (fromArea.startsWith('features/') && toArea === SESSION_LAYER) return true
  if (fromArea === 'shared') {
    return ALLOWED_SHARED_TO_FEATURE.some(
      (entry) => slashed(fromFile).endsWith(entry.from) && slashed(toPath).includes(entry.to),
    )
  }
  return false
}
