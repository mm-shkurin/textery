import { useSyncExternalStore } from 'react'
import { avatarSnapshot, subscribeAvatar } from './avatarStore'

// The object URL of the account's picture, or null when there is none (or none yet).
//
// It takes no effect and starts nothing: the fetch is driven by the identity snapshot, so every
// mounted avatar reads the same value and none of them can trigger a second download.
export function useAvatarUrl(): string | null {
  return useSyncExternalStore(subscribeAvatar, avatarSnapshot, avatarSnapshot)
}
