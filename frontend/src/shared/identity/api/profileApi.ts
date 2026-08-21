// The two operations of `/api/v1/auth/me`, and the wire→app boundary for both.
//
// There is no re-GET after a rename: PATCH answers with the FULL profile, so the client updates
// its identity snapshot from the response it already holds. And the value in that response is the
// NORMALIZED one (trim + NFC), not an echo of what was sent — a name typed with a trailing space
// comes back trimmed. Callers must recompute "unsaved" against the response, never against what
// they sent, or such a name stays dirty forever after a successful save.
import { isHttpError } from '../../api/httpClient'
import { authorizedRequest } from '../../session/authorizedRequest'
import { identityRequest } from './identityRequest'
import { NameRejectedError } from './profileErrors'
import { toProfile, type Profile } from './profileWire'
import { API } from '../../../shared/api/endpoints'

export { NameRejectedError } from './profileErrors'
// Re-exported so existing importers keep one import site for "the profile and how to get it".
export type { Profile } from './profileWire'

const ME_PATH = API.identity.me

// Never ends the session on failure — see identityRequest.
export async function fetchProfile(): Promise<Profile> {
  return toProfile(await identityRequest<Record<string, unknown>>(ME_PATH))
}

function nameRejection(error: unknown): NameRejectedError | null {
  if (!isHttpError(error) || error.status !== 400) return null
  const { error_code: code, message } = error.body
  return new NameRejectedError(
    typeof code === 'string' ? code : 'INVALID_NAME',
    typeof message === 'string' && message !== '' ? message : 'Имя не принято.',
  )
}

// PATCH goes through `authorizedRequest`, not `identityRequest`: this one IS user-initiated, so a
// renewal that fails here genuinely means the session is over and ending it is the honest answer.
//
// An empty string is not an error — it is "remove my name", and the backend answers 200 with
// `name: null`. Sending `{}` would mean "leave the name alone" (the tri-state the contract pins),
// which is the opposite instruction.
export async function saveProfileName(name: string): Promise<Profile> {
  try {
    return toProfile(
      await authorizedRequest<Record<string, unknown>>(ME_PATH, {
        method: 'PATCH',
        body: { name },
      }),
    )
  } catch (error) {
    const rejected = nameRejection(error)
    if (rejected !== null) throw rejected
    throw error
  }
}
