import { Link } from 'react-router-dom'

export const NOT_FOUND_TITLE = 'Документ не найден'
export const NOT_FOUND_EXPLANATION =
  'Документ удалён или принадлежит другому аккаунту. Откройте список своих документов и выберите нужный.'
export const DOCUMENTS_LIST_PATH = '/documents'
export const DOCUMENTS_LINK_TEXT = 'К моим документам'

// The whole screen, not a banner beside the editor: there is no document to edit, so the editor
// and the chat panel must not render at all. The way out is a real anchor (react-router `Link`)
// rather than a button — a blocked screen with no navigable exit is a dead end.
export function DocumentNotFoundBlocker() {
  return (
    <div className="ac-blocker" role="alert" data-testid="document-not-found">
      <h1 className="ac-blocker-title" data-testid="document-not-found-title">
        {NOT_FOUND_TITLE}
      </h1>
      <p className="ac-blocker-text">{NOT_FOUND_EXPLANATION}</p>
      <Link
        className="ac-blocker-link"
        to={DOCUMENTS_LIST_PATH}
        data-testid="document-not-found-documents-link"
      >
        {DOCUMENTS_LINK_TEXT}
      </Link>
    </div>
  )
}
