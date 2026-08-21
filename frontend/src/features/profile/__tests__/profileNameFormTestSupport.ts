// Shared fixtures for the display-name form's suites. Split out when the single test file passed
// the 200-line cap: the counter's two length units and the save/refusal paths are two readable
// groups, and they were only ever sharing this setup.
//
// `vi.mock` cannot live here — the registry is per test file — so each suite declares it. What is
// shared is the profile fixture and the two client stubs.
import { renderHook } from '@testing-library/react'
import { vi } from 'vitest'
import { useProfileNameForm } from '../hooks/useProfileNameForm'
import { saveProfileName } from '../../../shared/identity/api/profileApi'
import type { Profile } from '../../../shared/identity/api/profileApi'

export const EMOJI = '\u{1F600}'

export function profileNamed(name: string | null): Profile {
  return {
    email: 'ada@example.ru',
    name,
    createdAt: '2025-02-03T09:26:53Z',
    avatarUpdatedAt: null,
    hasPassword: true,
  }
}

export function formFor(name: string | null = null) {
  const dirt = { markDirty: vi.fn(), markClean: vi.fn() }
  const rendered = renderHook(() => useProfileNameForm(profileNamed(name), dirt))
  return { ...rendered, dirt }
}

// Every test states the whole behaviour of the client it runs against, rather than overriding a
// shared default. Layering a throwing implementation over a `mockResolvedValue` set in a
// `beforeEach` leaves two implementations on one mock and no way for a reader to tell which one
// answers — and the rejection the losing one produced belongs to nobody, which vitest reports as
// a failure of whichever test happened to be running.
export function respondsWith(profile: Profile): void {
  vi.mocked(saveProfileName).mockImplementation(async () => profile)
}

export function refusesWith(error: Error): void {
  vi.mocked(saveProfileName).mockImplementation(async () => {
    throw error
  })
}
