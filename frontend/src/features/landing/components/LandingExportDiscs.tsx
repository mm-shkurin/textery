import styles from './LandingExportDiscs.module.css'

// The gradient discs the frame sets beside the closing numbers, ending in the round «try it free»
// badge. Decorative. The fifth render is the one the quality bars are also filled with — the frame
// reuses it here, and so does this.
const DISCS = [
  '/design/landing/export-circle-1.webp',
  '/design/landing/export-circle-2.webp',
  '/design/landing/quality-bar-teal.webp',
  '/design/landing/export-circle-3.webp',
  '/design/landing/export-circle-4.webp',
]

export function LandingExportDiscs() {
  return (
    <div className={styles['export-discs']} aria-hidden="true">
      {DISCS.map((disc) => (
        <img src={disc} alt="" key={disc} />
      ))}
      <span className={styles['export-badge']}>↗</span>
    </div>
  )
}
