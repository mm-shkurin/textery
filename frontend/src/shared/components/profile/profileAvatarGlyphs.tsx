// Geometry only — no colour, no token, nothing the theme owns. It is inline rather than in a
// stylesheet because the disc's stylesheet is being rewritten onto theme tokens in a parallel
// session this sprint, and a second writer in that file would be a merge conflict for three
// declarations that no theme would ever want to change.
const PICTURE_STYLE = {
  width: '100%',
  height: '100%',
  borderRadius: '50%',
  // `cover`, so a portrait crop fills the circle instead of being letterboxed inside it. The
  // upload path already crops to a square, but a picture that predates it — or one the server
  // stored differently — must still not arrive stretched.
  objectFit: 'cover',
  display: 'block',
} as const

// `alt=""` and not a description: the wrapper is already `aria-hidden`, and the control around it
// carries the account's name. An alt here would be a second, competing label.
export function AvatarPicture({ url }: { url: string }) {
  return <img src={url} alt="" style={PICTURE_STYLE} data-testid="profile-avatar-picture" />
}

// The degraded disc's glyph. A failure that looked healthy would read as "an account with no
// name", and one that looked like the placeholder would read as "still loading" forever.
export function AvatarAlertGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" focusable="false">
      <path
        d="M12 4.5 21 20H3L12 4.5Z"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path d="M12 10v4.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <circle cx="12" cy="17.4" r="1" fill="currentColor" />
    </svg>
  )
}

// A ready account with no derivable initials gets this neutral figure rather than a fabricated
// letter: a placeholder initial is indistinguishable from a real one, and the user would read it
// as somebody else's account.
export function AvatarPersonGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" focusable="false">
      <circle cx="12" cy="8.5" r="3.75" fill="currentColor" />
      <path
        d="M4.75 19.25c0-3.31 3.25-5.5 7.25-5.5s7.25 2.19 7.25 5.5"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  )
}
