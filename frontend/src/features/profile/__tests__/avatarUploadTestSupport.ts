// Fixtures shared by the avatar hook's two suites, split out when the single test file passed the
// 200-line cap. Upload and removal are two independent paths: one decodes, resizes and sends
// bytes, the other sends nothing at all.
//
// `vi.mock` cannot live here — the registry is per test file — so each suite declares it. What is
// shared is the profile the server answers with, the resized blob, the file picker's output, and
// the fetch stub below.
import { vi } from 'vitest'
import { fetchAvatarBytes } from '../../../shared/identity/api/avatarApi'
import type { Profile } from '../../../shared/identity/api/profileApi'
import { stubObjectUrls } from './avatarTestSupport'

export const PROFILE: Profile = {
  email: 'ada@example.ru',
  name: null,
  createdAt: '2025-02-03T09:26:53Z',
  avatarUpdatedAt: '2026-08-14T12:00:00Z',
  hasPassword: true,
}

export const RESIZED = new Blob([new Uint8Array(2048)], { type: 'image/webp' })

export function aPicture(type = 'image/png', size = 1024): File {
  return new File([new Uint8Array(size)], 'photo', { type })
}

// Applying a profile whose `avatarUpdatedAt` changed makes every mounted avatar fetch its bytes.
// That fetch is mocked here, and it must RESOLVE a blob: a `vi.fn()` returning undefined throws
// inside the store's subscriber, which would surface as a failed upload on the happy path.
export function stubTheAvatarFetch(): void {
  stubObjectUrls()
  vi.mocked(fetchAvatarBytes).mockResolvedValue(new Blob([new Uint8Array(8)]))
}
