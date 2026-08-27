import { useCallback } from 'react'
import {
  DELETE_FAILURE_FALLBACK,
  RENAME_FAILURE_FALLBACK,
  deleteDocument,
  renameDocument,
} from '../api/documentActionsApi'
import { useRowAction } from './useRowAction'

/**
 * Переименование и удаление проекта из ленты.
 *
 * Лента перечитывается ПОСЛЕ успеха, а не правится на месте: сортировка и поиск живут на
 * сервере, и переименованная строка может уехать на другую страницу — локальная правка тогда
 * показала бы её там, где сервер её больше не отдаёт.
 *
 * Однопоточность действия и привязка ошибки к строке живут в `useRowAction` — это правила про
 * любое действие над строкой, а не про переименование.
 */
export function useProjectActions(reload: () => void) {
  const { run: runOnRow, pendingId, error } = useRowAction()

  const run = useCallback(
    (documentId: string, action: () => Promise<void>, fallback: string) => {
      runOnRow(documentId, action, fallback, reload)
    },
    [runOnRow, reload],
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
