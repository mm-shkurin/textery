import styles from './LandingTrustedBy.module.css'

// Figma `Desktop` → `Add` (node 862:6410): the row of who already uses the product, between the
// hero's stat cards and the three steps. It is the page's only third-party proof, and it was
// missing from the component tree entirely — the hero ran straight into «Процесс».
//
// Marks are the frame's own exports (SVG, so they stay sharp at any zoom and carry each brand's
// colour rather than a recolouring of it). They are decorative next to the name they sit beside,
// so the alt text is empty: a screen reader that announced «Яндекс Яндекс» would be reading the
// artwork and the label as two separate facts.
const PARTNERS = [
  { name: 'Яндекс', icon: '/design/icon-yandex.svg' },
  { name: 'Student Labs', icon: '/design/icon-student-labs.svg' },
  { name: 'ОмГТУ', icon: '/design/icon-omgtu.svg' },
]

export function LandingTrustedBy() {
  return (
    <section className={styles.trusted} data-testid="landing-trusted">
      {/* The four corner ticks are the design's frame around the caption — a crop-mark motif that
          repeats on the export section's badges. Drawn as spans rather than as one border so the
          corners stay square while the middle of each side stays open. */}
      <p className={styles['trusted-caption']}>
        <span aria-hidden="true" />
        <span aria-hidden="true" />
        <span aria-hidden="true" />
        <span aria-hidden="true" />
        нам доверяют
      </p>

      <ul className={styles['trusted-logos']}>
        {PARTNERS.map((partner) => (
          <li className={styles['trusted-logo']} key={partner.name}>
            <img src={partner.icon} alt="" decoding="async" />
            {partner.name}
          </li>
        ))}
      </ul>
    </section>
  )
}
