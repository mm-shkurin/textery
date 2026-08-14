import { useRef, useState } from 'react'
import { deleteAvatar, uploadAvatar } from '../../../shared/identity/api/avatarApi'
import { AvatarRejectedError } from '../../../shared/identity/api/profileErrors'
import { applyProfile } from '../../../shared/identity/identityStore'
import { avatarFileRejection, resizeAvatar } from '../utils/avatarImage'
import { avatarRejectionMessage, AVATAR_RESIZE_FAILED_MESSAGE } from '../utils/profileCopy'

// Picking, shrinking, sending and removing the picture.
//
// Two failure channels, and they are not interchangeable. A file the CLIENT refuses (wrong type,
// too many bytes) never leaves the browser and is reported inline next to the buttons — nothing
// happened, and the user's next move is to pick a different file. A request the SERVER refused or
// never answered gets the banner with «Повторить», the same treatment the name's save has.
export function useAvatarUpload() {
  const [busy, setBusy] = useState(false)
  const [rejection, setRejection] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  // Synchronous, unlike `busy`: two clicks in one tick both read the state React has not
  // re-rendered yet, and the account would get two uploads for one choice.
  const busyRef = useRef(false)
  // The last thing that failed, so «Повторить» repeats it instead of asking the user to find the
  // file again. A blob, not the File: the expensive part (decode + re-encode) is already done.
  const retryRef = useRef<(() => Promise<void>) | null>(null)

  async function run(action: () => Promise<void>): Promise<void> {
    if (busyRef.current) return
    busyRef.current = true
    setBusy(true)
    setRejection(null)
    setFailed(false)
    try {
      await action()
      retryRef.current = null
    } catch (error) {
      if (error instanceof AvatarRejectedError) {
        // The server's own refusal of the image. Inline, like a client-side one: it is still a
        // fact about the file, and «Повторить» on the identical bytes would fail identically.
        setRejection(avatarRejectionMessage(error.errorCode))
        retryRef.current = null
      } else {
        setFailed(true)
        retryRef.current = action
      }
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }

  async function upload(file: File): Promise<void> {
    // BEFORE the resize, and before anything is sent: a rejected file costs one comparison rather
    // than a decode of something the app already knows it will not use.
    const refused = avatarFileRejection(file)
    if (refused !== null) {
      setRejection(refused)
      setFailed(false)
      return
    }

    let bytes: Blob
    try {
      bytes = await resizeAvatar(file)
    } catch {
      // A file that says `image/png` and does not decode. Nothing was sent, so this is a
      // file-level complaint rather than a retryable failure.
      setRejection(AVATAR_RESIZE_FAILED_MESSAGE)
      setFailed(false)
      return
    }

    // No second GET: the PUT answers with the full profile, and the new `avatarUpdatedAt` is what
    // makes every mounted avatar pick up the new picture.
    await run(async () => applyProfile(await uploadAvatar(bytes)))
  }

  async function remove(): Promise<void> {
    await run(async () => applyProfile(await deleteAvatar()))
  }

  async function retry(): Promise<void> {
    const action = retryRef.current
    if (action !== null) await run(action)
  }

  return { busy, rejection, failed, upload, remove, retry }
}
