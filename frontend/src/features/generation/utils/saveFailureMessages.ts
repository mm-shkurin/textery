// What a failed document save tells the user. Pure and React-free — the save state machine in
// useDocumentSave consumes it, the same way it consumes autosaveRetryPolicy and autosaveDirtyGuard.
import { describeOperationFailure } from '../../../shared/api/failureText'
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
// That rule, and the one about the server's own words, now live in `shared/api/failureText.ts` —
// the projects feed was answering the same question in its own module. What is left here is the
// part that is only true of a save.
//
// A VersionConflictError reaching here is the same mistake one branch over. `saveDocument` already
// answers the FIRST 409 by refetching the version and retrying, so anything that arrives here has
// survived that — a second writer landed during the retry, or the refetch itself failed. The
// connection is not the problem, and reassuring the user their text is safe would be a promise this
// branch cannot keep: another save holds the document, and the next click re-enters the same race.
// Saying so lets the user reopen the document instead of clicking a button that will lose again.
export function describeSaveFailure(error: unknown): string {
  // Checked BEFORE the shared rule: a version conflict is an `Error` subclass carrying the
  // server's 409 text, and the sentence this screen needs is not that text but the one telling the
  // user to reopen the document.
  if (error instanceof VersionConflictError) return CONFLICT_ERROR_MESSAGE
  // `serverText: false` — this screen's sentence is an instruction, not a description of what
  // went wrong, and a 4xx's own wording does not carry the "your text is only in this tab" part
  // that is the whole point of showing anything here.
  return describeOperationFailure(error, SAVE_ERROR_MESSAGE, { serverText: false })
}
