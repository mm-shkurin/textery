import { useCallback, useState } from 'react'
import { describeFailure } from '../../../shared/api/send'

export interface RowActionError {
  id: string
  message: string
}

/**
 * Одно действие над лентой за раз, с ошибкой, привязанной к строке.
 *
 * Вынесено из `useProjectActions`: там это было тело `run` посреди двух тонких
 * обёрток, и правило про одновременные запросы читалось как деталь переименования,
 * хотя относится к любому действию над лентой.
 *
 * Два правила, и оба стоили ошибки:
 *
 * - **Пока одно действие в работе, следующее не стартует — ни по этой строке, ни по
 *   любой другой.** Гейт глобальный (`pendingId !== null`), а не построчный: «Удалить»
 *   дважды по строке, которая уже удаляется, получило бы 404 — ошибку о том, что всё
 *   сработало. Побочный эффект честно назван: клик по соседней строке, пока идёт
 *   удаление, молча не сработает. Лента всё равно перечитывается после успеха, так что
 *   два параллельных действия гонялись бы за один и тот же reload.
 * - **Ошибка хранится вместе с id строки**, а не одной на экран: баннер сверху
 *   заставил бы искать, о какой из двадцати карточек речь.
 */
export function useRowAction() {
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [error, setError] = useState<RowActionError | null>(null)

  const run = useCallback(
    (rowId: string, action: () => Promise<void>, fallback: string, onSuccess: () => void) => {
      if (pendingId !== null) return
      setPendingId(rowId)
      setError(null)
      action()
        .then(onSuccess)
        .catch((failure) => {
          setError({ id: rowId, message: describeFailure(failure, fallback) })
        })
        .finally(() => {
          setPendingId(null)
        })
    },
    [pendingId],
  )

  return { run, pendingId, error }
}
