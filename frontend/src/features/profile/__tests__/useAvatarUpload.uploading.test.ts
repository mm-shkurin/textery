import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAvatarUpload } from '../hooks/useAvatarUpload'
import { uploadAvatar } from '../../../shared/identity/api/avatarApi'
import { AvatarRejectedError } from '../../../shared/identity/api/profileErrors'
import { resizeAvatar } from '../utils/avatarImage'
import { resetIdentity } from '../../../shared/identity/identityStore'
import type { Profile } from '../../../shared/identity/api/profileApi'
import { aPicture, PROFILE, RESIZED, stubTheAvatarFetch } from './avatarUploadTestSupport'

// Two failure channels that must never be confused. A file the CLIENT refuses never leaves the
// browser: nothing happened, the message belongs beside the buttons, and «Повторить» would be a
// lie because there is nothing to repeat. A request the SERVER refused or never answered is a
// different story — and only the second kind is retryable.

vi.mock('../../../shared/identity/api/avatarApi', () => ({
  uploadAvatar: vi.fn(),
  deleteAvatar: vi.fn(),
  fetchAvatarBytes: vi.fn(),
}))
vi.mock('../utils/avatarImage', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../utils/avatarImage')>()),
  resizeAvatar: vi.fn(),
}))

describe('uploading', () => {
  beforeEach(() => {
    stubTheAvatarFetch()
    vi.mocked(resizeAvatar).mockResolvedValue(RESIZED)
    vi.mocked(uploadAvatar).mockResolvedValue(PROFILE)
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
    resetIdentity()
  })

  it('sends the resized bytes rather than the file that was picked', async () => {
    const { result } = renderHook(() => useAvatarUpload())

    await act(async () => await result.current.upload(aPicture()))

    expect(vi.mocked(uploadAvatar).mock.calls[0][0]).toBe(RESIZED)
    expect(result.current.rejection).toBeNull()
    expect(result.current.failed).toBe(false)
  })

  it('refuses an unsupported file before it decodes anything', async () => {
    // One comparison, rather than a decode of something the app already knows it will not use.
    const { result } = renderHook(() => useAvatarUpload())

    await act(async () => await result.current.upload(aPicture('image/svg+xml')))

    expect(result.current.rejection).toContain('этот формат')
    expect(resizeAvatar).not.toHaveBeenCalled()
    expect(uploadAvatar).not.toHaveBeenCalled()
  })

  it('reports a file that claims a type it cannot decode, without offering a retry', async () => {
    // Nothing was sent, so this is a fact about the file — repeating it would fail identically.
    vi.mocked(resizeAvatar).mockRejectedValue(new Error('avatar: decode failed'))
    const { result } = renderHook(() => useAvatarUpload())

    await act(async () => await result.current.upload(aPicture()))

    expect(result.current.rejection).toBe(
      'Не удалось прочитать изображение — попробуйте другой файл.',
    )
    expect(result.current.failed).toBe(false)
    expect(uploadAvatar).not.toHaveBeenCalled()
  })

  it("shows the server's own refusal inline and does not arm a retry", async () => {
    vi.mocked(uploadAvatar).mockRejectedValue(
      new AvatarRejectedError('AVATAR_DIMENSIONS_TOO_LARGE', 'ignored'),
    )
    const { result } = renderHook(() => useAvatarUpload())

    await act(async () => await result.current.upload(aPicture()))

    expect(result.current.rejection).toBe(
      'Изображение слишком большое по размеру — выберите другое.',
    )
    expect(result.current.failed).toBe(false)
  })

  it('translates an unrecognised refusal code into a sentence rather than nothing', async () => {
    vi.mocked(uploadAvatar).mockRejectedValue(new AvatarRejectedError('SOMETHING_NEW', 'ignored'))
    const { result } = renderHook(() => useAvatarUpload())

    await act(async () => await result.current.upload(aPicture()))

    expect(result.current.rejection).toBe('Изображение не принято — попробуйте другое.')
  })

  it('offers a retry when the server never answered', async () => {
    vi.mocked(uploadAvatar).mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const { result } = renderHook(() => useAvatarUpload())

    await act(async () => await result.current.upload(aPicture()))
    expect(result.current.failed).toBe(true)

    await act(async () => await result.current.retry())

    expect(uploadAvatar).toHaveBeenCalledTimes(2)
    expect(result.current.failed).toBe(false)
  })

  it('retries with the already-resized bytes, not the file', async () => {
    // The expensive half — decode and re-encode — is already done, and the user should not have
    // to find the file again.
    vi.mocked(uploadAvatar).mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const { result } = renderHook(() => useAvatarUpload())
    await act(async () => await result.current.upload(aPicture()))

    await act(async () => await result.current.retry())

    expect(resizeAvatar).toHaveBeenCalledTimes(1)
    expect(vi.mocked(uploadAvatar).mock.calls[1][0]).toBe(RESIZED)
  })

  it('does nothing on a retry when nothing failed', async () => {
    const { result } = renderHook(() => useAvatarUpload())
    await act(async () => await result.current.upload(aPicture()))

    await act(async () => await result.current.retry())

    expect(uploadAvatar).toHaveBeenCalledTimes(1)
  })

  it('ignores a second choice made while the first is still in flight', async () => {
    // Two clicks in one tick both read a `busy` React has not re-rendered yet; the account would
    // get two uploads for one choice.
    let release: (profile: Profile) => void = () => {}
    vi.mocked(uploadAvatar).mockImplementation(
      () => new Promise<Profile>((resolve) => (release = resolve)),
    )
    const { result } = renderHook(() => useAvatarUpload())

    await act(async () => {
      void result.current.upload(aPicture())
      await Promise.resolve()
      void result.current.upload(aPicture())
      await Promise.resolve()
      release(PROFILE)
    })

    await waitFor(() => expect(result.current.busy).toBe(false))
    expect(uploadAvatar).toHaveBeenCalledTimes(1)
  })
})
