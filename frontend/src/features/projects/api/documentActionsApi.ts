import { send } from '../../../shared/api/send'
import { API } from '../../../shared/api/endpoints'

/**
 * Два действия над проектом из ленты: переименовать и удалить.
 *
 * Живут здесь, а не в `generation/api/documentApi.ts`, потому что вызывает их «Мои проекты», а
 * не редактор, и правило границ модулей запрещает фиче лезть в чужую. Транспорт общий (`send`),
 * то есть оба несут токен сессии и переживают его протухание тем же способом, что весь продукт.
 */

export const RENAME_FAILURE_FALLBACK = 'Не удалось переименовать проект'
export const DELETE_FAILURE_FALLBACK = 'Не удалось удалить проект'

interface DocumentResponse {
  id: string
  content: string
  version: number
}

/**
 * Переименование.
 *
 * Отдельного эндпоинта для названия нет: контракт умеет `PUT /documents/{id}` целиком, и он
 * ТРЕБУЕТ и content, и version — сохранить один заголовок нечем. Поэтому сначала GET, потом PUT
 * с тем же телом и новым названием: документ уходит на сервер ровно тем, каким оттуда пришёл,
 * а меняется только строка, которую пользователь и правил.
 *
 * Цена честная и записана здесь: два запроса вместо одного и окно между ними, в котором чужое
 * сохранение (вторая вкладка, редактор) может уехать вперёд. Тогда PUT ответит 409, и это
 * правильный ответ — переименование не должно затирать текст, набранный секунду назад. Ловит
 * его вызывающий и показывает сообщение, а не молча повторяет.
 */
export async function renameDocument(documentId: string, title: string): Promise<void> {
  const current = await send<DocumentResponse>(
    API.documents.one(documentId),
    { method: 'GET' },
    RENAME_FAILURE_FALLBACK,
  )
  await send<DocumentResponse>(
    API.documents.one(documentId),
    { method: 'PUT', body: { content: current.content, title, version: current.version } },
    RENAME_FAILURE_FALLBACK,
  )
}

/**
 * Удаление.
 *
 * 204 на успехе, 404 — если своего документа с таким id нет. Второй DELETE того же id отвечает
 * 404, а не 204, и это не «уже удалено, всё хорошо»: клиент, который считает «его и так нет»
 * успехом, спрячет удаление, попавшее не в тот id, — единственную ошибку этого эндпоинта,
 * которую пользователь отменить не может.
 */
export async function deleteDocument(documentId: string): Promise<void> {
  // 204 без тела: общий транспорт читает пустое тело как «докладывать нечего» и отдаёт `{}`,
  // поэтому отдельного режима ответа здесь не нужно.
  await send<void>(API.documents.one(documentId), { method: 'DELETE' }, DELETE_FAILURE_FALLBACK)
}
