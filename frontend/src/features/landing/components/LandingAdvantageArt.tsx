import styles from './LandingAdvantageArt.module.css'

// The illustration inside each «Возможности» card (Figma `Desktop` → `Advantages`, node
// 1337:6860). Four different compositions, not four images: the frame overlaps two or three
// renders per card and lets them bleed past the card's edge, and the first and third also carry a
// skeleton of grey lines standing in for the document being written.
//
// Split out of `LandingAdvantages` so that file stays a list of four claims and their copy. All of
// it is decorative: the card's heading and paragraph already say what the picture shows, so the
// whole block is hidden from assistive technology rather than given four invented alt texts.
export type AdvantageArtKind = 'ai' | 'editor' | 'pdf' | 'backup'

function Skeleton() {
  return (
    <div className={styles['art-skeleton']}>
      <i />
      <i />
      <i />
      <i />
    </div>
  )
}

export function LandingAdvantageArt({ kind }: { kind: AdvantageArtKind }) {
  return (
    <div className={`${styles.art} ${styles[`art-${kind}`]}`} aria-hidden="true">
      {(kind === 'ai' || kind === 'pdf') && <Skeleton />}

      {kind === 'ai' && (
        <>
          <img
            className={styles['art-splash']}
            src="/design/landing/feature-ai-splash.webp"
            alt=""
          />
          <img className={styles['art-chart']} src="/design/landing/feature-ai-chart.webp" alt="" />
          <img className={styles['art-dots']} src="/design/landing/feature-ai-dots.webp" alt="" />
        </>
      )}

      {kind === 'editor' && (
        <>
          {/* The star is the frame's own vector, exported rather than redrawn — it is a
              nine-pointed asterisk, not a font glyph, and the `✳` that stood in for it here was a
              different shape at every font stack. */}
          <img
            className={styles['art-star']}
            src="/design/landing/feature-editor-star.svg"
            alt=""
          />
          <img
            className={styles['art-letter']}
            src="/design/landing/feature-editor-letter.svg"
            alt=""
          />
        </>
      )}

      {kind === 'pdf' && (
        <img className={styles['art-pdf']} src="/design/landing/feature-pdf.webp" alt="" />
      )}

      {kind === 'backup' && (
        <>
          <img
            className={styles['art-cloud']}
            src="/design/landing/feature-backup-cloud.webp"
            alt=""
          />
          <img
            className={styles['art-case']}
            src="/design/landing/feature-backup-case.webp"
            alt=""
          />
        </>
      )}
    </div>
  )
}
