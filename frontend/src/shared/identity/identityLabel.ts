import type { Profile } from './api/profileApi'

// Who this account IS, in one line: the display name when there is one, the address otherwise.
//
// The address never disappears — it is what the user signs in with, and it keeps its own row on
// the profile screen. This is only about which of the two is the headline.
export function identityLabel(profile: Profile): string {
  const name = profile.name?.trim() ?? ''
  return name === '' ? profile.email : name
}
