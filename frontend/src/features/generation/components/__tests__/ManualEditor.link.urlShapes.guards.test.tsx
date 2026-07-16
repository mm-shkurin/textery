import { describe, it, vi } from 'vitest'
import { applyLinkUrl, expectSoleLink } from './ManualEditor.link.testSupport'

vi.mock('../../api/documentApi')

// All four shapes below are GREEN today and are NOT a red phase.
//
// That is the finding, not an accident of writing them: today's naive
// `normalizeHref` (prefix http:// unless HAS_SCHEME matches) already gets every
// one of them right, precisely *because* it is naive — it has no email branch
// and no host-shape regex to get wrong. Verified by executing the real
// `isAllowedUri` from @tiptap/extension-link against each, not by reading it.
//
// They exist to constrain `green-frontend-url-shapes`, which must add both an
// email branch and a structural host discriminator to satisfy the five skipped
// tests in ManualEditor.link.urlShapes.test.tsx. Two review passes each wrote a
// candidate green that passes all 7 fixtures in that file and breaks the rows
// below. Every row here names the specific candidate that kills it, and each
// was confirmed by running that candidate — a guard nothing plausible breaks is
// a guard not worth its line count.
//
// Kept in a separate file from the five reds for the 200-line limit; the shared
// setup/assertion helpers moved to ManualEditor.link.testSupport.tsx.
//
// Three of the four rows are mutation-tested kill guards: a candidate green was
// run against each, and each row is the only one that fails it. The `https://`
// + `@` row is regression coverage instead — no candidate kills it alone — and
// says so in its own comment rather than borrowing the others' authority.
describe('ManualEditor link URL shapes — normalization guards', () => {
  // Killed by: `IS_EMAILish(u) ? 'mailto:'+u : ...` — the shape both review
  // passes independently reached for. It yields `mailto:youtube.com/@vsauce`,
  // which passes isAllowedUri via the `mailto:` alternative (executed: allowed
  // = true), so the anchor RENDERS, raises no alert, and is saved. Silently
  // wrong beats loudly wrong for damage. `/@handle` URLs — vk.com/@durov,
  // Mastodon, Medium — are ordinary sources for this product.
  it('an @ in a path is a URL, not an email, and is normalized to http://', async () => {
    const contentArea = await applyLinkUrl('youtube.com/@vsauce')

    expectSoleLink(contentArea, 'http://youtube.com/@vsauce')
  })

  // COVERAGE, not a kill guard — the distinction is deliberate, and this row is
  // the one place in these two files where the two come apart.
  //
  // The `!url.startsWith('mailto:')` candidate does turn this into
  // `mailto:https://youtube.com/@vsauce` (executed: isAllowedUri allows it, so
  // it renders). But the row above kills that candidate too — executed, both
  // rows fail together. An earlier draft of this comment claimed the row above
  // "cannot catch it"; that was reasoning, and it was wrong.
  //
  // No plausible green is killed by this row alone: every @-based email
  // predicate loose enough to misfire on the scheme'd form is at least as loose
  // on the bare form above, because each schemeless discriminator (`://`,
  // `startsWith('mailto:')`, HAS_SCHEME, strip-scheme-then-test) exempts this
  // input and not that one. Two candidates tried, both died on both rows.
  //
  // Kept anyway, on the honest reason: `https://example.com/x` pins a scheme
  // surviving and `mailto:a@b.com` pins an `@` surviving, but nothing pins the
  // two TOGETHER, and the mailto: branch green must add is exactly what could
  // couple them. Four lines of regression coverage over a gap the fixtures
  // leave open — not a mutation-tested guard, and labelled as such so nobody
  // later trusts a kill claim this row cannot back.
  it('a scheme + @ URL passes through untouched rather than being re-prefixed', async () => {
    const contentArea = await applyLinkUrl('https://youtube.com/@vsauce')

    expectSoleLink(contentArea, 'https://youtube.com/@vsauce')
  })

  // Killed by the natural structural fix for the host-port reds: a positive
  // ASCII host-shape regex, e.g. /^[a-z0-9-]+(\.[a-z0-9-]+)*(:\d+)?([\/?#]|$)/i.
  // It passes all 7 and leaves a Cyrillic host unprefixed — and isAllowedUri's
  // `[^a-z]` alternative then ADMITS the bare host (executed: allowed = true),
  // so it renders as a relative URL against our own origin. That is exactly the
  // harm the http:// prefix exists to prevent (LinkPopover.tsx:7-11), aimed at
  // every .рф citation in an editor whose content is Russian.
  it('a Cyrillic IDN bare host is normalized to http:// like any other bare host', async () => {
    const contentArea = await applyLinkUrl('кремль.рф')

    expectSoleLink(contentArea, 'http://кремль.рф')
  })

  // Pins the FALLBACK, which was unpinned by construction: the 7 existing
  // fixtures each match a *branch*, so nothing constrains input matching none.
  //
  // Killed by a green the row above passes — which is what earns it its line
  // count, and is NOT the all-ASCII gate an earlier draft named here. That gate
  // (`/^[\x00-\x7F]*$/`, "non-ASCII → leave alone") leaves кремль.рф bare too,
  // so the row above already kills it; it justifies nothing on its own.
  //
  // The green only this row catches makes the host unicode-aware and the path
  // ASCII by accident:
  //   /^[\p{L}\p{N}-]+(\.[\p{L}\p{N}-]+)*(:\d+)?([\/?#][\w\/%.-]*)?$/u
  // `\w` stays ASCII-only even under /u — the classic JS trap — so `Война_и_мир`
  // fails the path class, the whole URL is left bare, and isAllowedUri's
  // `[^a-z]` alternative admits it relative to our origin. Executed: this green
  // passes all 5 reds, all 7 fixtures, and кремль.рф above, and fails only here.
  //
  // That is the separation this row exists for — "unicode-aware host" from
  // "unicode-aware URL" — and a Wikipedia citation is the most likely real URL
  // in this product to carry it.
  it('an ASCII host with a Cyrillic path is normalized to http://', async () => {
    const contentArea = await applyLinkUrl('ru.wikipedia.org/wiki/Война_и_мир')

    expectSoleLink(contentArea, 'http://ru.wikipedia.org/wiki/Война_и_мир')
  })
})
