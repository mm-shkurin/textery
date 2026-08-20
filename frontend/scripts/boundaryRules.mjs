// Which parts of src/ are allowed to import which, and the exceptions that are written down.
//
// README states the layering ("shared не видит никого"), and until now nothing enforced it. A prose
// rule about imports is a rule that holds until the first afternoon somebody needs a component from
// another feature and reaches for a `../../` — which is not a decision anyone makes deliberately, it
// is one made while looking at something else.
//
// The rule, in one line: a feature may import itself and `shared`. Anything else crossing a feature
// boundary has to be listed below, with a reason.

// The session layer used to live at `features/auth`, and every generic thing that needed the
// signed-in identity had to reach DOWN into a feature to get it — eight rows of written-down
// exceptions saying "this one is upside down, but it was the right call". The real fix, named in
// those rows, was a session module outside `features/`: it is `shared/session` now
// (`authSession`, `authorizedRequest`, `refreshApi`, `sessionTokens`, `accountEmail`), so every
// row is gone and the dependency direction holds without exceptions. The auth SCREENS stayed in
// `features/auth` — they are a feature; the session is not.
export const ALLOWED_SHARED_TO_FEATURE = []

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
  if (fromArea === 'shared') {
    return ALLOWED_SHARED_TO_FEATURE.some(
      (entry) => slashed(fromFile).endsWith(entry.from) && slashed(toPath).includes(entry.to),
    )
  }
  return false
}
