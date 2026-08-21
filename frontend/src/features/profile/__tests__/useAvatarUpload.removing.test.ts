import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAvatarUpload } from '../hooks/useAvatarUpload'
import { deleteAvatar } from '../../../shared/identity/api/avatarApi'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { PROFILE, stubTheAvatarFetch } from './avatarUploadTestSupport'

// Removal sends no bytes, so none of the upload suite's decode/resize machinery applies. What it
// shares with upload is the one rule about failure: a request that never reached the server is
// retryable, and says so.

vi.mock('../../../shared/identity/api/avatarApi', () => ({
  uploadAvatar: vi.fn(),
  deleteAvatar: vi.fn(),
  fetchAvatarBytes: vi.fn(),
}))

describe('removing', () => {
  beforeEach(() => {
    stubTheAvatarFetch()
    vi.mocked(deleteAvatar).mockResolvedValue(PROFILE)
  })
  afterEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
    resetIdentity()
  })

  it('clears the picture and reports no failure', async () => {
    const { result } = renderHook(() => useAvatarUpload())

    await act(async () => await result.current.remove())

    expect(deleteAvatar).toHaveBeenCalledTimes(1)
    expect(result.current.failed).toBe(false)
  })

  it('offers a retry when the removal did not reach the server', async () => {
    vi.mocked(deleteAvatar).mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const { result } = renderHook(() => useAvatarUpload())

    await act(async () => await result.current.remove())
    expect(result.current.failed).toBe(true)

    await act(async () => await result.current.retry())

    expect(deleteAvatar).toHaveBeenCalledTimes(2)
    expect(result.current.failed).toBe(false)
  })
})
