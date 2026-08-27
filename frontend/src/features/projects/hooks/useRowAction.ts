import { useCallback, useState } from 'react'
import { describeFailure } from '../../../shared/api/send'

export interface RowActionError {
  id: string
  message: string
}

/**
 * Одно действие над одной строкой ленты за раз, с ошибкой, привязанной к строке.
 *
 * Вынесено из `useProjectActions`: там это было тело `run` посреди двух тонких
 * обёрток, и правило «второй запрос по той же строке не отправляется» читалось
 * как деталь переименования, хотя относится к любому действию над строкой.
 *
 * Два правила, и оба стоили ошибки:
 *
 * - **Пока одно действие в работе, следующее не стартует.** «Удалить» дважды по
 *   строке, которая уже удаляется, получило бы 404 — ошибку о том, что всё
 *   сработало.
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
