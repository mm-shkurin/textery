import styles from './ManualEditorTopbar.module.css'
import { ManualEditorSaveStatus } from './ManualEditorSaveStatus'
import { ExportControl } from './ExportControl'
import { BackIcon } from './EditorIcons'

interface ManualEditorTopbarProps {
  documentTypeLabel: string
  // Из генерации — открыт после готового текста; иначе редактор открыли вручную и это
  // надо назвать, иначе два разных пути к одному экрану выглядят одинаково.
  showManualModeChip: boolean
  documentId: string | null
  hasUnsavedChanges: boolean
  isSaving: boolean
  isRetryPending: boolean
  hasFailedToInitialize: boolean
  onBack: () => void
  onSave: () => void
  save: () => void | Promise<void>
}

/**
 * Верхняя полоса редактора: выход назад, что за документ, состояние сохранения и два
 * действия — «Сохранить» и «Скачать».
 *
 * По фрейму. Собрана из того, что редактор УМЕЕТ, а не из того, что нарисовано: на макете
 * в этой полосе стоят иконка «домой», переименование документа и счётчик слов. Домой ведёт
 * не всегда (`onBack` возвращает туда, откуда пришли), переименования нет в контракте, а
 * слова никто не считает — вместо счётчика стоит статус сохранения, который у компонента
 * есть и который пользователю нужнее: без него автосохранение выглядит бездействием.
 */
export function ManualEditorTopbar({
  documentTypeLabel,
  showManualModeChip,
  documentId,
  hasUnsavedChanges,
  isSaving,
  isRetryPending,
  hasFailedToInitialize,
  onBack,
  onSave,
  save,
}: ManualEditorTopbarProps) {
  return (
    <div className={styles['edf-topbar']}>
      <button type="button" className={styles['edf-back']} onClick={onBack}>
        <BackIcon />
        Назад
      </button>

      {/* Тип документа — единственное на экране подтверждение, что редактируется именно
          доклад. Testid прежний: это тот же объект, что раньше рисовали хлебные крошки. */}
      <div className={styles['edf-title-block']} data-testid="editor-breadcrumb">
        <span className={styles['edf-chip']}>{documentTypeLabel}</span>
        {showManualModeChip && <span className={styles['edf-chip']}>Ручной режим</span>}
      </div>

      <div className={styles['edf-topbar-actions']}>
        <ManualEditorSaveStatus
          documentId={documentId}
          hasUnsavedChanges={hasUnsavedChanges}
          isRetryPending={isRetryPending}
          hasFailedToInitialize={hasFailedToInitialize}
        />
        {/*
          aria-disabled, а не нативный disabled: пока идёт сохранение, кнопка должна
          продолжать принимать клики, чтобы намерение «сохранить ещё раз» дошло до
          собственной защиты save(). Нативно отключённая кнопка не рассылает click вовсе
          (это спека, а не причуда jsdom), и нажатие было бы молча потеряно.
        */}
        <button
          type="button"
          className={`${styles['edf-btn']} ${styles['edf-btn-quiet']}`}
          aria-disabled={isSaving}
          onClick={onSave}
        >
          {isSaving && (
            <span
              data-testid="save-spinner"
              className={styles['edf-save-spinner']}
              aria-hidden="true"
            />
          )}
          Сохранить
        </button>
        <ExportControl documentId={documentId} hasUnsavedChanges={hasUnsavedChanges} save={save} />
      </div>
    </div>
  )
}
