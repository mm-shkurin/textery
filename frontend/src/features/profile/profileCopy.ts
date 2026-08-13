import { NAME_MAX_CODE_POINTS } from '../../shared/identity/nameValue'

// The screen's words, in one file so a wording change is not a hunt through the markup.

// The count is in the sentence on purpose: «слишком длинное» leaves the user to work out by how
// much, on a field whose counter they may not have looked at.
export function overLengthMessage(count: number): string {
  return `Имя длиннее ${NAME_MAX_CODE_POINTS} символов — сейчас ${count}. Уберите хотя бы один символ.`
}

export const RAW_INPUT_TOO_LARGE_MESSAGE = 'Слишком много введённого текста — сократите имя.'

// The backend's two refusal codes, in the user's language. The codes are distinguishable by
// design (`NAME_INPUT_TOO_LARGE` for the raw pre-normalization gate, `INVALID_NAME` for the
// domain bound and for characters a name may not contain) and they are given different sentences
// here for the same reason: two refusals that read identically cannot be told apart on screen
// any more than in a client's `switch`.
export function nameRejectionMessage(errorCode: string): string {
  if (errorCode === 'NAME_INPUT_TOO_LARGE') return RAW_INPUT_TOO_LARGE_MESSAGE
  if (errorCode === 'INVALID_NAME') {
    return `Такое имя нельзя сохранить: не длиннее ${NAME_MAX_CODE_POINTS} символов и без служебных знаков.`
  }
  // An unrecognised code still gets a sentence rather than a blank field — the save did fail, and
  // the reason the user cares about is that it did.
  return 'Имя не сохранено — проверьте значение.'
}

export const SAVE_FAILED_MESSAGE =
  'Не удалось сохранить имя — сервер не ответил. Введённое сохранено, попробуйте ещё раз.'

export const LOAD_FAILED_TITLE = 'Не удалось загрузить профиль'
export const LOAD_FAILED_BODY =
  'Данные учётной записи сейчас недоступны. Ничего не потеряно — попробуйте ещё раз через минуту.'
