// `POST /api/v1/auth/me/deletion` — the one irreversible operation in the product.
//
// The request body is one of two shapes, and WHICH one is decided by the account, not by the
// client's preference: an account created with email + password proves the deletion with that
// password; an account that only ever signed in through an OAuth provider has no password to
// type and proves it by typing its own address instead. `profile.hasPassword` is the only thing
// that can tell them apart.
//
// The response is 204 with no body. There is nothing to map, and a client that expected a profile
// back would be waiting for a row that no longer exists.
import { isHttpError } from '../../api/httpClient'
import { authorizedRequest } from '../../../features/auth/api/authorizedRequest'
import { DeletionRejectedError } from './profileErrors'
import { deletionStub, profileStubEnabled } from './profileStub'
import type { Profile } from './profileWire'

const DELETION_PATH = '/api/v1/auth/me/deletion'

export type DeletionConfirmation =
  { kind: 'password'; password: string } | { kind: 'email'; email: string }

// Which proof this account can give. `hasPassword === true` is the ONLY case that gets a password
// field: both `false` (an OAuth account) and `null`/`undefined` (the backend has not sent the flag
// yet) fall back to the address.
//
// That fallback is chosen because of how each way of being wrong fails. Showing an address field
// to somebody who does have a password costs them one 400 they can read and recover from, with
// the session intact. Showing a password field to somebody who has none is a dead end inside the
// product — there is no password to type and no other way out of the account. So the recoverable
// error is the one we take.
export function deletionConfirmationKind(profile: Profile): 'password' | 'email' {
  return profile.hasPassword === true ? 'password' : 'email'
}

function deletionRejection(error: unknown): DeletionRejectedError | null {
  if (!isHttpError(error) || error.status !== 400) return null
  const { message } = error.body
  return new DeletionRejectedError(
    typeof message === 'string' && message !== ''
      ? message
      : 'Подтверждение не принято. Проверьте введённое.',
  )
}

export async function requestAccountDeletion(confirmation: DeletionConfirmation): Promise<void> {
  if (profileStubEnabled()) return deletionStub(confirmation)
  const body =
    confirmation.kind === 'password'
      ? { password: confirmation.password }
      : { confirm_email: confirmation.email }
  try {
    await authorizedRequest<unknown>(DELETION_PATH, { method: 'POST', body })
  } catch (error) {
    const rejected = deletionRejection(error)
    if (rejected !== null) throw rejected
    throw error
  }
}
