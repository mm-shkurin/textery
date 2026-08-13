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
  // Whether this account has a password at all, which decides HOW it proves an account deletion:
  // a password account types its password, an OAuth-only account types its own address. The
  // client cannot work this out for itself — nothing it holds says how the account was created —
  // so showing a password field to somebody who has only ever signed in with Yandex would lock
  // them inside an account they cannot leave.
  //
  // OPTIONAL and three-valued on purpose. `null` means the backend did not send the field, which
  // is the state of the world until the backend session adds it; `undefined` keeps every existing
  // `Profile` literal (including the parallel theme session's test fixtures) compiling. Both fall
  // back to the address confirmation — see `deletionConfirmationKind`.
  hasPassword?: boolean | null
}

export function toProfile(body: Record<string, unknown>): Profile {
  const name = body.name
  const avatarUpdatedAt = body.avatar_updated_at
  const hasPassword = body.has_password
  return {
    // Anything that is not a boolean — a missing key, a null, a string — is `null`, which reads
    // "the backend did not tell us". It is deliberately NOT coerced to false: `Boolean(undefined)`
    // and a genuine `false` would become the same value, and one of them is a fact while the
    // other is an absence.
    hasPassword: typeof hasPassword === 'boolean' ? hasPassword : null,
    email: typeof body.email === 'string' ? body.email : '',
    name: typeof name === 'string' && name !== '' ? name : null,
    createdAt: typeof body.created_at === 'string' ? body.created_at : '',
    avatarUpdatedAt:
      typeof avatarUpdatedAt === 'string' && avatarUpdatedAt !== '' ? avatarUpdatedAt : null,
  }
}
