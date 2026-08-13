// A local stand-in for `/api/v1/auth/me` while the backend session builds the real one.
//
// TEMPORARY, and structured so removing it is one deleted file plus three call sites in
// profileApi.ts. It is OFF unless `VITE_PROFILE_STUB=1` is set — never a fallback that engages
// when a real request fails, which would turn a production outage into fabricated identity on
// screen.
//
// It imitates the two behaviours the screen is built against and would otherwise only discover
// against the live backend: the response carries the NORMALIZED value (trim + NFC), and the
// length bound counts CODE POINTS of that normalized value.
import { NameRejectedError } from './profileErrors'
import { countCodePoints, NAME_MAX_CODE_POINTS, normalizeName } from '../nameValue'
import type { Profile } from './profileApi'

const LATENCY_MS = 400

let stubName: string | null = 'Анна Ковалёва'

export function profileStubEnabled(): boolean {
  return import.meta.env.VITE_PROFILE_STUB === '1'
}

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS))
}

function snapshot(): Profile {
  return { email: 'anna.ivanova@example.com', name: stubName, createdAt: '2025-02-03T09:26:53Z' }
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
