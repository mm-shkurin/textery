import { LandingSection } from './LandingSection'
import { LandingCtaButton } from './LandingCtaButton'
import landingSectionStyles from './LandingSection.module.css'
import styles from './LandingCta.module.css'

interface LandingCtaProps {
  onPrimaryCtaClick?: () => void
}

// Figma `Desktop` → `CTA` (node 1290:11260): the page's closing block — an eyebrow, a two-line
// 44/53 heading whose second half is brand blue, one line of reassurance, and the free-trial
// button, centred inside a ring of rounded document thumbnails.
//
// The ring IS drawn now: the frame's tiles were exported with this pass, ten of them, each a
// square render rotated 21.2° further than the one before so the row bends into an arc around the
// text. The two 3D letters that sit at the foot of the arc are the same artwork, and the «T» is
// mirrored because the frame rotates it 175.6° — visually a flip, not a turn.
//
// Every tile is decorative: the ask is the heading and the button, and ten alt texts describing
// gradients would be ten pieces of noise between a reader and that button.
const TILES = [
  { file: 'cta-tile-01', left: '44.5%', top: '2%', rotate: 0 },
  { file: 'cta-tile-03', left: '27%', top: '7%', rotate: 21.2 },
  { file: 'cta-tile-10', left: '62%', top: '7%', rotate: -21.2 },
  { file: 'cta-tile-02', left: '12%', top: '23%', rotate: 42.4 },
  { file: 'cta-tile-09', left: '77%', top: '23%', rotate: -42.4 },
  { file: 'cta-tile-04', left: '2%', top: '48%', rotate: 63.5 },
  { file: 'cta-tile-08', left: '87%', top: '48%', rotate: -63.5 },
]
export function LandingCta({ onPrimaryCtaClick }: LandingCtaProps) {
  return (
    <LandingSection testId="landing-cta" className={styles['landing-cta']}>
      <div className={styles['landing-cta-tiles']} aria-hidden="true">
        {TILES.map((tile) => (
          <img
            className={styles['landing-cta-tile']}
            key={tile.file}
            src={`/design/landing/${tile.file}.webp`}
            alt=""
            style={{ left: tile.left, top: tile.top, transform: `rotate(${tile.rotate}deg)` }}
          />
        ))}
        <img
          className={`${styles['landing-cta-letter']} ${styles['landing-cta-letter-t']}`}
          src="/design/landing/cta-letter-t.webp"
          alt=""
        />
        <img
          className={`${styles['landing-cta-letter']} ${styles['landing-cta-letter-at']}`}
          src="/design/landing/cta-letter-at.webp"
          alt=""
        />
      </div>

      <div className={landingSectionStyles['landing-section-head']}>
        <span className={landingSectionStyles['landing-eyebrow']}>Передовой сервис</span>
        <h2 className={styles['landing-cta-title']}>
          Создайте <span className={styles['landing-cta-accent']}>первый текстовый документ</span>{' '}
          за 30 секунд
        </h2>
        <p className={landingSectionStyles['landing-section-lead']}>
          Без регистрации. Без кредитной карты. Просто попробуйте прямо сейчас.
        </p>
      </div>

      <LandingCtaButton
        onClick={onPrimaryCtaClick}
        wrapperClassName={styles['landing-cta-action']}
        testId="cta-primary-cta"
        label="Попробовать бесплатно"
      />
    </LandingSection>
  )
}
