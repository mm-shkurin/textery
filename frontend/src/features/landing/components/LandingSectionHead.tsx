import type { ReactNode } from 'react'
import landingSectionStyles from './LandingSection.module.css'

// Every landing section opens the same way: an eyebrow, a heading and a lead paragraph, in that
// order, wearing the shared section classes. Six components had that block written out by hand,
// which is why a change to the shell — a class rename, an element swap, an aria attribute — had
// to be made six times and could be forgotten in one.
//
// The overrides exist because one section genuinely differs: the comparison table tightens its
// eyebrow, title and lead. They are class ADDITIONS, never replacements, so a section cannot
// quietly drop out of the shared shell while still using it. The CTA is deliberately NOT built on
// this — its heading wears its own class instead of the shared one, and forcing it through here
// would mean adding a class it does not want or making the shared one optional, which is the same
// as not having a shell.
interface LandingSectionHeadProps {
  eyebrow: ReactNode
  title: ReactNode
  lead: ReactNode
  eyebrowClassName?: string
  titleClassName?: string
  leadClassName?: string
}

function joined(base: string, extra?: string): string {
  return extra ? `${base} ${extra}` : base
}

export function LandingSectionHead({
  eyebrow,
  title,
  lead,
  eyebrowClassName,
  titleClassName,
  leadClassName,
}: LandingSectionHeadProps) {
  return (
    <div className={landingSectionStyles['landing-section-head']}>
      <span className={joined(landingSectionStyles['landing-eyebrow'], eyebrowClassName)}>
        {eyebrow}
      </span>
      <h2 className={joined(landingSectionStyles['landing-section-title'], titleClassName)}>
        {title}
      </h2>
      <p className={joined(landingSectionStyles['landing-section-lead'], leadClassName)}>{lead}</p>
    </div>
  )
}
