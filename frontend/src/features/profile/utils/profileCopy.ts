import { NAME_MAX_CODE_POINTS } from '../../../shared/identity/nameValue'

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

export const AVATAR_RESIZE_FAILED_MESSAGE =
  'Не удалось прочитать изображение — попробуйте другой файл.'

export const AVATAR_FAILED_MESSAGE =
  'Не удалось отправить изображение — сервер не ответил. Попробуйте ещё раз.'

// The server's three refusals of an image. Reachable even though the client downscales first: it
// bounds bytes and type, and the server additionally bounds pixel dimensions — a picture can pass
// here and still be refused there.
export function avatarRejectionMessage(errorCode: string): string {
  if (errorCode === 'AVATAR_TOO_LARGE') return 'Изображение слишком тяжёлое — выберите другое.'
  if (errorCode === 'AVATAR_UNSUPPORTED_TYPE') {
    return 'Такой формат изображения не поддерживается — подойдёт PNG, JPEG или WebP.'
  }
  if (errorCode === 'AVATAR_DIMENSIONS_TOO_LARGE') {
    return 'Изображение слишком большое по размеру — выберите другое.'
  }
  return 'Изображение не принято — попробуйте другое.'
}

// The one sentence that tells a user what "delete my account" actually costs. It names the
// documents and the generations, not just "your account": those are the user's own texts, and
// this block is the only place in the product where anyone finds out they go too. It is not there
// to frighten anybody out of leaving — it is there so that nobody leaves without knowing.
export const DELETION_TITLE = 'Удаление аккаунта'
export const DELETION_WARNING =
  'Аккаунт, все ваши документы и генерации будут удалены безвозвратно. Отменить это будет нельзя.'
// The frame's own words (node 1202:6227): the dialog names the act in its title and spells out
// what is lost before it asks for anything.
export const DELETION_CONFIRM_TITLE = 'Удалить аккаунт?'
export const DELETION_CONSEQUENCE =
  'Действие необратимо: будут удалены все проекты, сгенерированные документы и история правок. ' +
  'Восстановить данные после подтверждения невозможно.'
export const DELETION_PASSWORD_HINT = 'Введите пароль от аккаунта, чтобы подтвердить удаление.'
export const DELETION_FAILED_MESSAGE =
  'Не удалось удалить аккаунт — сервер не ответил. Аккаунт на месте, попробуйте ещё раз.'

export function deletionEmailHint(email: string): string {
  return `Введите адрес аккаунта — ${email} — чтобы подтвердить удаление.`
}

export const LOAD_FAILED_TITLE = 'Не удалось загрузить профиль'
export const LOAD_FAILED_BODY =
  'Данные учётной записи сейчас недоступны. Ничего не потеряно — попробуйте ещё раз через минуту.'
