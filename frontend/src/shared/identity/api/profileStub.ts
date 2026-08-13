// A local stand-in for `/api/v1/auth/me` and its avatar routes while the backend session builds
// the real ones.
//
// TEMPORARY, and structured so removing it is one deleted file plus the call sites in
// profileApi.ts / avatarApi.ts. It is OFF unless `VITE_PROFILE_STUB=1` is set — never a fallback
// that engages when a real request fails, which would turn a production outage into fabricated
// identity on screen.
//
// It imitates the behaviours the screen is built against and would otherwise only discover
// against the live backend: the rename response carries the NORMALIZED value (trim + NFC), the
// length bound counts CODE POINTS of it, and an upload changes `avatar_updated_at` — which is
// what makes every mounted avatar refetch its bytes.
import { DeletionRejectedError, NameRejectedError } from './profileErrors'
import type { DeletionConfirmation } from './deleteAccountApi'
import { countCodePoints, NAME_MAX_CODE_POINTS, normalizeName } from '../nameValue'
import type { Profile } from './profileWire'

const LATENCY_MS = 400

let stubName: string | null = 'Анна Ковалёва'
let stubAvatar: Blob | null = null
let stubAvatarUpdatedAt: string | null = null
// Not `Date.now()`: the stub only needs a value that CHANGES per upload, and a counter says that
// without pretending to be a timestamp anybody should parse.
let stubAvatarVersion = 0

export function profileStubEnabled(): boolean {
  return import.meta.env.VITE_PROFILE_STUB === '1'
}

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS))
}

function snapshot(): Profile {
  return {
    email: 'anna.ivanova@example.com',
    name: stubName,
    createdAt: '2025-02-03T09:26:53Z',
    avatarUpdatedAt: stubAvatarUpdatedAt,
    hasPassword: STUB_HAS_PASSWORD,
  }
}

export function stubbedProfile(): Promise<Profile> {
  return delay(snapshot())
}

export async function stubbedRename(name: string): Promise<Profile> {
  const normalized = normalizeName(name)
  if (countCodePoints(normalized) > NAME_MAX_CODE_POINTS) {
    await delay(null)
    throw new NameRejectedError('INVALID_NAME', 'Имя не принято.')
  }
  stubName = normalized === '' ? null : normalized
  return delay(snapshot())
}

export function stubbedAvatarUpload(bytes: Blob): Promise<Profile> {
  stubAvatar = bytes
  stubAvatarVersion += 1
  stubAvatarUpdatedAt = `2026-08-13T00:00:${String(stubAvatarVersion).padStart(2, '0')}Z`
  return delay(snapshot())
}

export function stubbedAvatarDelete(): Promise<Profile> {
  stubAvatar = null
  stubAvatarUpdatedAt = null
  return delay(snapshot())
}

// The stub for the account this checkout signs in as has a password, so the local screen shows
// the password field. Flip it to `false` to see the OAuth-only path, which is what an account
// with no password gets and what the client also falls back to while `has_password` is missing
// from `GET /me`.
const STUB_HAS_PASSWORD = true
const STUB_PASSWORD = 'Str0ng!Pass'

export async function deletionStub(confirmation: DeletionConfirmation): Promise<void> {
  await delay(null)
  const matches =
    confirmation.kind === 'password'
      ? confirmation.password === STUB_PASSWORD
      : confirmation.email === snapshot().email
  // The stub REFUSES a wrong value rather than always succeeding: the refusal path is the one
  // that must leave the session alive, and a stub that cannot fail cannot show that.
  if (!matches) {
    throw new DeletionRejectedError('Подтверждение не принято. Проверьте введённое.')
  }
}

export async function stubbedAvatarBytes(): Promise<Blob> {
  if (stubAvatar === null) throw new Error('stub: no avatar')
  return delay(stubAvatar)
}
