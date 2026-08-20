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
// The picture control's position, as ONE value. The two failure channels are mutually exclusive
// by construction here — a file the client refused is never also a request that failed — which is
// exactly what four independent switches could not say.
interface AvatarState {
  busy: boolean
  rejection: string | null
  failed: boolean
  // How many avatar writes have landed — the confirmation toast keys off it, the same way the
  // name form's does.
  savedCount: number
}

const IDLE: AvatarState = { busy: false, rejection: null, failed: false, savedCount: 0 }

export function useAvatarUpload() {
  const [state, setState] = useState<AvatarState>(IDLE)
  // Synchronous, unlike `busy`: two clicks in one tick both read the state React has not
  // re-rendered yet, and the account would get two uploads for one choice.
  const busyRef = useRef(false)
  // The last thing that failed, so «Повторить» repeats it instead of asking the user to find the
  // file again. A blob, not the File: the expensive part (decode + re-encode) is already done.
  const retryRef = useRef<(() => Promise<void>) | null>(null)

  async function run(action: () => Promise<void>): Promise<void> {
    if (busyRef.current) return
    busyRef.current = true
    setState((current) => ({ ...current, busy: true, rejection: null, failed: false }))
    try {
      await action()
      // Counted only on the path that actually wrote: the design's «Изменения сохранены» alert
      // fires «после загрузки/удаления фото», not after a refused file.
      setState((current) => ({ ...current, savedCount: current.savedCount + 1 }))
      retryRef.current = null
    } catch (error) {
      if (error instanceof AvatarRejectedError) {
        // The server's own refusal of the image. Inline, like a client-side one: it is still a
        // fact about the file, and «Повторить» on the identical bytes would fail identically.
        setState((current) => ({
          ...current,
          rejection: avatarRejectionMessage(error.errorCode),
        }))
        retryRef.current = null
      } else {
        setState((current) => ({ ...current, failed: true }))
        retryRef.current = action
      }
    } finally {
      busyRef.current = false
      setState((current) => ({ ...current, busy: false }))
    }
  }

  async function upload(file: File): Promise<void> {
    // BEFORE the resize, and before anything is sent: a rejected file costs one comparison rather
    // than a decode of something the app already knows it will not use.
    const refused = avatarFileRejection(file)
    if (refused !== null) {
      setState((current) => ({ ...current, rejection: refused, failed: false }))
      return
    }

    let bytes: Blob
    try {
      bytes = await resizeAvatar(file)
    } catch {
      // A file that says `image/png` and does not decode. Nothing was sent, so this is a
      // file-level complaint rather than a retryable failure.
      setState((current) => ({
        ...current,
        rejection: AVATAR_RESIZE_FAILED_MESSAGE,
        failed: false,
      }))
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

  return {
    busy: state.busy,
    rejection: state.rejection,
    failed: state.failed,
    savedCount: state.savedCount,
    upload,
    remove,
    retry,
  }
}
