import { act } from '@testing-library/react'
import { vi } from 'vitest'

// Debounced-autosave debounce interval (ms). Single source of truth shared by the E3.1
// (autosave) and E3.2 (failed autosave) fake-timer tests so both advance the same boundary.
export const AUTOSAVE_DEBOUNCE_MS = 1000

// Fake-timer settle: drain the pending microtask queue (resolved/rejected save promises,
// their .then/.catch, and the React state updates they schedule) without advancing wall
// clock. Must run under vi.useFakeTimers(); wraps in act() so the flushed updates commit.
export async function flushMicrotasks() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0)
  })
}
