import { useCallback, useEffect, useRef, useState } from 'react'
import { useDismissOnOutside } from '../../../shared/hooks/useDismissOnOutside'
import { MoreIcon } from './ProjectsIcons'
import styles from './ProjectCardMenu.module.css'

export interface ProjectActions {
  onRename: (documentId: string, title: string) => void
  onDelete: (documentId: string) => void
  // Идёт ли сейчас запрос по ЭТОМУ проекту. Пока идёт, пункты недоступны: второе нажатие
  // «Удалить» по строке, которая уже удаляется, отправило бы второй DELETE и получило 404 —
  // ошибку о том, что всё сработало.
  busy?: boolean
}

interface ProjectCardMenuProps extends ProjectActions {
  documentId: string
  title: string
  testId: string
}

/**
 * «···» на карточке и в строке таблицы: переименовать или удалить проект.
 *
 * До этого кнопка была нарисована и отключена — «действия появятся позже». Оба действия
 * контракт умеет уже сегодня: `DELETE /documents/{id}` есть, а переименование делается через
 * `PUT` тем же телом с новым названием (см. `documentActionsApi`), поэтому рисовать заглушку
 * дальше было нечестно.
 *
 * Показывается ТОЛЬКО у документа. У генерации нет ни своего DELETE, ни названия, которое
 * можно править, — там кнопки нет вовсе, а не есть с пустым меню.
 */
export function ProjectCardMenu({
  documentId,
  title,
  testId,
  onRename,
  onDelete,
  busy = false,
}: ProjectCardMenuProps) {
  const [open, setOpen] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [draft, setDraft] = useState(title)
  const containerRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Фокус возвращается на кнопку, а не в никуда: закрытие уничтожает элемент, который держал
  // фокус, и браузер паркует его на <body> — клавиатурный пользователь оказывается в начале
  // страницы вместо строки, с которой работал.
  const close = useCallback(() => {
    setOpen(false)
    setRenaming(false)
    triggerRef.current?.focus()
  }, [])

  useDismissOnOutside(open, containerRef, close)

  // Фокус переводится ЭФФЕКТОМ, а не атрибутом autoFocus: атрибут забирает фокус в момент
  // появления элемента где угодно на странице (в том числе при восстановлении прокрутки), а
  // здесь фокус нужен ровно тогда, когда пользователь сам выбрал «Переименовать».
  useEffect(() => {
    if (renaming) inputRef.current?.focus()
  }, [renaming])

  const submitRename = () => {
    const next = draft.trim()
    // Пустое название и название без изменений — не переименование: первое стёрло бы
    // единственное, чем строка опознаётся в ленте, второе стоило бы двух запросов впустую.
    if (next === '' || next === title) {
      close()
      return
    }
    onRename(documentId, next)
    close()
  }

  return (
    <div className={styles['project-menu']} ref={containerRef}>
      <button
        type="button"
        ref={triggerRef}
        className={styles['project-menu-trigger']}
        data-testid={testId}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Действия: ${title}`}
        disabled={busy}
        onClick={() => {
          setDraft(title)
          setRenaming(false)
          setOpen((wasOpen) => !wasOpen)
        }}
      >
        <MoreIcon />
      </button>

      {open && !renaming && (
        <div className={styles['project-menu-panel']} role="menu">
          <button
            type="button"
            role="menuitem"
            className={styles['project-menu-item']}
            data-testid={`${testId}-rename`}
            onClick={() => setRenaming(true)}
          >
            Переименовать
          </button>
          {/* Удаление названо опасным цветом и стоит последним: соседство с «Переименовать»
              делает промах в один пиксель необратимым, и цвет — единственное, что об этом
              предупреждает до нажатия. */}
          <button
            type="button"
            role="menuitem"
            className={`${styles['project-menu-item']} ${styles['project-menu-item-danger']}`}
            data-testid={`${testId}-delete`}
            onClick={() => {
              onDelete(documentId)
              close()
            }}
          >
            Удалить
          </button>
        </div>
      )}

      {open && renaming && (
        // Форма, а не поле с кнопкой: Enter должен отправлять — это то, что делает браузер сам,
        // и переизобретать его обработчиком клавиш значит потерять половину случаев (IME, ввод
        // с экранной клавиатуры телефона).
        <form
          className={styles['project-menu-panel']}
          onSubmit={(event) => {
            event.preventDefault()
            submitRename()
          }}
        >
          <input
            className={styles['project-menu-input']}
            data-testid={`${testId}-rename-input`}
            aria-label="Новое название проекта"
            ref={inputRef}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Escape') close()
            }}
          />
          <div className={styles['project-menu-actions']}>
            <button type="button" className={styles['project-menu-quiet']} onClick={close}>
              Отмена
            </button>
            <button
              type="submit"
              className={styles['project-menu-primary']}
              data-testid={`${testId}-rename-submit`}
            >
              Сохранить
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
