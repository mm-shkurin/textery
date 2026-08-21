import styles from './GenerationHeading.module.css'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'

interface GenerationHeadingProps {
  documentTypeLabel: string
}

// Mockup 01/04-generation-form.html: the topic-entry surface is introduced by a breadcrumb
// carrying the picked document type, then "Новая генерация" / "Опишите, что нужно получить".
//
// The mockup's breadcrumb carries a *second* chip ("Автоматический режим"). Story 18 removed
// the mode modal — a type pick now lands straight here — so there is no mode to name and the
// chip would be a constant label decorating a choice the user never makes. Only the type chip
// survives; it is the sole on-screen confirmation of what was just picked.
//
// The mockup's "← Назад" control is deliberately absent: this component takes no navigation
// callback, and inventing one would be a behaviour change, not an alignment.
export function GenerationHeading({ documentTypeLabel }: GenerationHeadingProps) {
  return (
    <>
      <div className={styles['cw-breadcrumb']}>
        <span className={styles['cw-breadcrumb-chip']} data-testid="generation-breadcrumb">
          <span className={styles['cw-chip-icon']}>
            <PlaceholderImage />
          </span>
          {documentTypeLabel}
        </span>
      </div>
      <h1 className={styles['cw-title']}>Новая генерация</h1>
      <p className={styles['cw-subtitle']}>Опишите, что нужно получить</p>
    </>
  )
}
