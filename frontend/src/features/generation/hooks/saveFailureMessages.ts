// What a failed document save tells the user. Pure and React-free — the save state machine in
// useDocumentSave consumes it, the same way it consumes autosaveRetryPolicy and autosaveDirtyGuard.
import { SessionExpiredError } from '../../auth/api/authorizedRequest'
import { VersionConflictError } from '../../../shared/api/send'

export const SAVE_ERROR_MESSAGE =
  'Не удалось сохранить. Повторите — текст пока только в редакторе, не потеряйте вкладку.'

// Deliberately does NOT say "попробуйте ещё раз": retrying is what just failed. Reopening is the
// only action that can succeed, and it costs the text in this editor — so the message says that
// outright rather than letting the user discover it by losing the paragraph twice.
export const CONFLICT_ERROR_MESSAGE =
  'Документ был изменён другим сохранением. Откройте его заново, чтобы увидеть актуальную версию — текст в этом редакторе не сохранён.'

// The default is for a network blip: retrying may recover, so it asks for that — but it does NOT
// reassure the text is "сохранён локально": there is no persistence anywhere (content lives only in
// Tiptap's in-memory state), so it warns the tab is the only copy instead.
//
// An expired session is not a failure of the save: the request was fine, the user is signed out.
// `authorizedRequest` raises SessionExpiredError precisely so callers can tell the two apart, and
// `send` goes out of its way to rethrow it untouched — but NOTHING narrowed it, so the whole
// carve-out was unconsumed machinery and the save catch flattened it right back into "check your
// connection", telling a signed-out user to retry a button that cannot work until they sign in.
// Its own message ("Сессия истекла. Войдите снова.") is the accurate thing to show.
//
// A VersionConflictError reaching here is the same mistake one branch over. `saveDocument` already
// answers the FIRST 409 by refetching the version and retrying, so anything that arrives here has
// survived that — a second writer landed during the retry, or the refetch itself failed. The
// connection is not the problem, and reassuring the user their text is safe would be a promise this
// branch cannot keep: another save holds the document, and the next click re-enters the same race.
// Saying so lets the user reopen the document instead of clicking a button that will lose again.
export function describeSaveFailure(error: unknown): string {
  if (error instanceof SessionExpiredError) return error.message
  if (error instanceof VersionConflictError) return CONFLICT_ERROR_MESSAGE
  return SAVE_ERROR_MESSAGE
}
