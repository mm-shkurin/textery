import { useCallback, useState } from 'react'
import {
  DELETE_FAILURE_FALLBACK,
  RENAME_FAILURE_FALLBACK,
  deleteDocument,
  renameDocument,
} from '../api/documentActionsApi'
import { describeFailure } from '../../../shared/api/send'

interface ProjectActionError {
  id: string
  message: string
}

/**
 * Переименование и удаление проекта из ленты.
 *
 * Лента перечитывается ПОСЛЕ успеха, а не правится на месте: сортировка и поиск живут на
 * сервере, и переименованная строка может уехать на другую страницу — локальная правка тогда
 * показала бы её там, где сервер её больше не отдаёт.
 *
 * Ошибка хранится вместе с id строки, а не одной на экран: баннер сверху заставил бы искать,
 * о какой из двадцати карточек речь.
 */
export function useProjectActions(reload: () => void) {
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [error, setError] = useState<ProjectActionError | null>(null)

  const run = useCallback(
    (documentId: string, action: () => Promise<void>, fallback: string) => {
      // Второй запрос по той же строке не отправляется: «Удалить» дважды по строке, которая уже
      // удаляется, получило бы 404 — ошибку о том, что всё сработало.
      if (pendingId !== null) return
      setPendingId(documentId)
      setError(null)
      action()
        .then(() => {
          reload()
        })
        .catch((failure) => {
          setError({ id: documentId, message: describeFailure(failure, fallback) })
        })
        .finally(() => {
          setPendingId(null)
        })
    },
    [pendingId, reload],
  )

  const rename = useCallback(
    (documentId: string, title: string) => {
      run(documentId, () => renameDocument(documentId, title), RENAME_FAILURE_FALLBACK)
    },
    [run],
  )

  const remove = useCallback(
    (documentId: string) => {
      run(documentId, () => deleteDocument(documentId), DELETE_FAILURE_FALLBACK)
    },
    [run],
  )

  return { rename, remove, pendingId, error }
}
