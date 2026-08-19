import { useEffect, useState } from 'react'

// The «Изменения сохранены» alert — Figma node 1227:9790, a 637x64 black pill at a 16px radius,
// centred against the bottom of the screen, with its 16/600 label in white.
//
// The frame's own note says when it appears: «alert появляется — при изменении имени; после
// загрузки/удаления фото». Those are the three writes this screen makes, and until now each of
// them finished in silence — the field simply stopped saying «Сохраняем имя…».
//
// `role="status"`, not `role="alert"`: this is a confirmation, and an assertive live region
// interrupts whatever a screen-reader user is reading to announce that nothing went wrong.
const VISIBLE_MS = 3200

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
    const timer = setTimeout(() => setVisible(false), VISIBLE_MS)
    // Cleared on the next save as well as on unmount, or a second save inside the window would
    // leave the first timer to hide the toast early.
    return () => clearTimeout(timer)
  }, [saveCount])

  if (!visible) return null

  return (
    <div className="profile-saved-toast" role="status" data-testid="profile-saved-toast">
      Изменения сохранены
    </div>
  )
}
