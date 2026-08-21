// The three avatar operations of `/api/v1/auth/me/avatar`.
//
// THE ONE THING TO KNOW HERE: the image cannot be shown with `<img src="/api/v1/auth/me/avatar">`.
// The browser issues that request itself and attaches no `Authorization` header — the access
// token lives in sessionStorage, not in a cookie — so the endpoint answers 401 and every user
// gets a broken image. The bytes have to be fetched by the app, with the token, and handed to the
// <img> as an object URL.
//
// The GET goes through `identityRequest`, the same path as `GET /me`: it fires unprompted on page
// load, so a 5xx or a failed renewal must NEVER end the session. The PUT and the DELETE are
// user-initiated and go through `authorizedRequest`, where a dead session is honestly reported as
// one.
import { isHttpError } from '../../api/httpClient'
import { authorizedRequest } from '../../session/authorizedRequest'
import { identityRequest } from './identityRequest'
import { AvatarRejectedError } from './profileErrors'
import { toProfile, type Profile } from './profileWire'
import { API } from '../../../shared/api/endpoints'

const AVATAR_PATH = API.identity.avatar

// `image/webp` because that is what the client encodes to — see `avatarImage.ts`. The server
// stores bytes and does not decode them, so this header is the only statement of what they are.
const AVATAR_CONTENT_TYPE = 'image/webp'

function avatarRejection(error: unknown): AvatarRejectedError | null {
  if (!isHttpError(error) || error.status !== 400) return null
  const { error_code: code, message } = error.body
  return new AvatarRejectedError(
    typeof code === 'string' ? code : 'AVATAR_UNSUPPORTED_TYPE',
    typeof message === 'string' && message !== '' ? message : 'Изображение не принято.',
  )
}

// Raw bytes in the body — not FormData, not multipart. `httpClient` passes a Blob through
// untouched; anything else there would be JSON-stringified into the string "{}".
export async function uploadAvatar(bytes: Blob): Promise<Profile> {
  try {
    return toProfile(
      await authorizedRequest<Record<string, unknown>>(AVATAR_PATH, {
        method: 'PUT',
        headers: { 'Content-Type': AVATAR_CONTENT_TYPE },
        body: bytes,
      }),
    )
  } catch (error) {
    const rejected = avatarRejection(error)
    if (rejected !== null) throw rejected
    throw error
  }
}

export async function deleteAvatar(): Promise<Profile> {
  return toProfile(
    await authorizedRequest<Record<string, unknown>>(AVATAR_PATH, { method: 'DELETE' }),
  )
}

// Only ever called when `avatarUpdatedAt` is non-null. Asking unconditionally would put a 404 in
// the console on every page load of every account that has no picture — the common case.
export async function fetchAvatarBytes(): Promise<Blob> {
  return identityRequest<Blob>(AVATAR_PATH, { responseType: 'blob' })
}
