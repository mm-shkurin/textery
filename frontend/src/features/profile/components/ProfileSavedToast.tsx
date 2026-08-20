import { useEffect, useState } from 'react'
import { RUNTIME } from '../../../shared/config/runtime'

// The «Изменения сохранены» alert — Figma node 1227:9790, a 637x64 black pill at a 16px radius,
// centred against the bottom of the screen, with its 16/600 label in white.
//
// The frame's own note says when it appears: «alert появляется — при изменении имени; после
// загрузки/удаления фото». Those are the three writes this screen makes, and until now each of
// them finished in silence — the field simply stopped saying «Сохраняем имя…».
//
// An `<output>`: the element IS a polite live region natively, which is what a confirmation
// wants — `role="alert"` would interrupt whatever a screen-reader user is reading to tell them
// that nothing went wrong.
//
// How long it stays is a tunable, not a component's business: `RUNTIME.profileSavedToastMs`.

interface ProfileSavedToastProps {
  // Bumped by the caller on every successful write. A counter rather than a boolean: two saves in
  // a row must re-show the toast, and a boolean that is already `true` cannot.
  saveCount: number
}

export function ProfileSavedToast({ saveCount }: ProfileSavedToastProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (saveCount === 0) return
    setVisible(true)
    const timer = setTimeout(() => setVisible(false), RUNTIME.profileSavedToastMs)
    // Cleared on the next save as well as on unmount, or a second save inside the window would
    // leave the first timer to hide the toast early.
    return () => clearTimeout(timer)
  }, [saveCount])

  if (!visible) return null

  return (
    <output className="profile-saved-toast" data-testid="profile-saved-toast">
      Изменения сохранены
    </output>
  )
}
