// The profile as it arrives on the wire, and the one place snake_case becomes camelCase.
//
// Its own module because THREE clients now answer with a full profile — `GET /me`, `PATCH /me`,
// and both avatar routes — and a shared mapper in any one of them would have the other importing
// the module that imports it.
export interface Profile {
  email: string
  // Always PRESENT on the wire, `null` when unset — never absent. `null` is the one stored
  // representation of "no name", so an account that never had one and an account that cleared
  // one are indistinguishable here, by design.
  name: string | null
  createdAt: string
  // `null` means there is no picture, and that is the fact the client checks BEFORE asking for
  // bytes. Its value is also the cache key: when the string changes the picture changed, which is
  // what tells a header holding an old object URL to fetch again.
  avatarUpdatedAt: string | null
}

export function toProfile(body: Record<string, unknown>): Profile {
  const name = body.name
  const avatarUpdatedAt = body.avatar_updated_at
  return {
    email: typeof body.email === 'string' ? body.email : '',
    name: typeof name === 'string' && name !== '' ? name : null,
    createdAt: typeof body.created_at === 'string' ? body.created_at : '',
    avatarUpdatedAt:
      typeof avatarUpdatedAt === 'string' && avatarUpdatedAt !== '' ? avatarUpdatedAt : null,
  }
}
