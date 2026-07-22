import { describe, it, vi } from 'vitest'
import { applyLinkUrl, expectSoleLink, expectRejected } from './ManualEditor.link.testSupport'

vi.mock('../../api/documentApi')

// red-frontend-url-shapes-3 — pins normalizeHref's OUTPUT, not just which
// branch it takes. The five earlier reds and the four guards constrained the
// *discriminator* (which branch fires); these constrain what each branch is
// allowed to EMIT. The distinction has teeth because green-frontend-url-shapes
// widened the path class to `\S*`, which pulled a family of dead/deceptive
// inputs OUT of the fallback and INTO the HOST_SHAPE branch, where they now
// report success — a red aimed only at the fallback would have passed while
// they shipped.
//
// RED rows are it.skip with a dated reason: they pin behaviour green must
// build, and leaving them failing would break the committed 112-green suite
// (this scenario's standing convention for its reds — see the pre-fix state of
// ManualEditor.link.urlShapes.test.tsx). GREEN regression guards stay live.
describe('ManualEditor link URL shapes — normalized output', () => {
  // GROUP 1 — the HOST_SHAPE branch is unrejectable by construction, so nothing
  // stops it emitting an href that cannot be used. Everything it matches is
  // prefixed `http://`, and isAllowedUri — the only downstream validator — vets
  // the SCHEME only, so `http` always passes. `example.com:99999999999` has a
  // port past 65535: today → href `http://example.com:99999999999`, NO alert,
  // linked and persisted (ManualEditor.tsx save) — yet `new URL()` throws on it,
  // so it is dead on click. RED today: the anchor renders (length 1), so
  // expectRejected fails on the length-0 assert.
  // Rule pinned: a HOST_SHAPE-matched input whose normalized href does not
  // new URL()-parse must be REJECTED. Kills a green that keeps the blind
  // `http://` prefix without a post-normalization parse check.
  it('RED: a host with an out-of-range port is rejected, not linked to a dead http:// href', async () => {
    const contentArea = await applyLinkUrl('example.com:99999999999')

    expectRejected(contentArea)
  })

  // GROUP 2 — invisible / control characters. U+00AD (Word's soft hyphen — the
  // realistic vector is pasting a wiki URL out of Word), U+200B, U+202E (a known
  // RTL-override spoofing char) and C0 controls. Fixture: a host with a soft
  // hyphen inside `example`.
  //
  // Branch it actually flows through (verified by execution, agent-review on
  // `026a026` — corrected from an earlier draft that misattributed it to
  // HOST_SHAPE): U+00AD is Unicode category Cf, NOT in `[\p{L}\p{N}-]`, so
  // `HOST_SHAPE.test('exa­mple.com')` is FALSE. The input falls to the
  // FALLBACK (`return url`, bare `exa­mple.com`), and `isAllowedUri`'s
  // relative-form alternative treats the soft hyphen as a word boundary and
  // accepts it — so the anchor renders today with NO alert. (`new URL()` on the
  // bare string THROWS; it is a schemeless/relative href, not a parsed
  // `host=example.com` — the opposite of what the first draft claimed.)
  // Disposition decided by the orchestrator: REJECT (not strip, not accept).
  // RED today: the anchor renders, expectRejected fails length-0.
  //
  // Implication for green: the character screen must sit on the OUTPUT / fallback
  // path (or on every branch), NOT only inside HOST_SHAPE — a green that screens
  // chars only in the host branch leaves this vector open.
  it('RED: a host containing an invisible soft-hyphen is rejected, not linked as a deceptive http:// href', async () => {
    const contentArea = await applyLinkUrl('exa­mple.com')

    expectRejected(contentArea)
  })

  // GROUP 3 — the scheme-vs-host discriminator, one rung below the localhost
  // ladder. `tel:79001234567` and `localhost:3000` are structurally identical
  // (word, colon, digits), so no regex over the string's shape separates them —
  // only a known-scheme set can. `localhost:3000`/`myserver:8080` are pinned as
  // HOSTS in urlShapes.test.tsx; `tel:` must stay a SCHEME. Today HOST_SHAPE
  // matches `tel:79001234567` → `http://tel:79001234567` (links). RED: the href
  // must be EXACTLY the untouched input.
  it('RED: a tel: URL with a plain number passes through unchanged, not prefixed http://', async () => {
    const contentArea = await applyLinkUrl('tel:79001234567')

    expectSoleLink(contentArea, 'tel:79001234567')
  })

  // GROUP 3, second scheme — forces green to key on the SET of known schemes,
  // not to hardcode `tel`. `sms` is likewise word:digits and likewise permitted
  // by isAllowedUri (verified against the installed extension-link: http, https,
  // ftp, ftps, mailto, tel, callto, sms, cid, xmpp). Today → `http://sms:...`
  // (links). RED: must pass through as `sms:79001234567`. A green that special-
  // cases the string `tel` passes the row above and fails this one.
  it('RED: an sms: URL with a plain number also passes through unchanged, proving the scheme set is not hardcoded to tel', async () => {
    const contentArea = await applyLinkUrl('sms:79001234567')

    expectSoleLink(contentArea, 'sms:79001234567')
  })

  // GROUP 3 regression guard — GREEN today and must STAY green. `javascript:`
  // is not in isAllowedUri's set, so today the unprefixed scheme reaches
  // isAllowedUri, is rejected, setLink returns false, and the alert shows. The
  // scheme-passthrough fix green must add for tel:/sms: MUST NOT turn this into
  // a live `javascript:` href. Live, not skipped: it constrains green now.
  it('a javascript: URL stays rejected — the scheme-passthrough fix must not admit it', async () => {
    const contentArea = await applyLinkUrl('javascript:alert(1)')

    expectRejected(contentArea)
  })

  // GROUP 4 — the fallback, `return url` (LinkPopover.tsx:24, fully uncovered).
  // `/docs`, `#anchor`, `?q=1` match no branch, so today each is returned BARE —
  // a relative URL against our own origin, exactly the harm LinkPopover.tsx:7-11
  // says the `http://` prefix exists to prevent. isAllowedUri's `[^a-z]`
  // alternative admits a leading `/`, `#` or `?`, so all three LINK today.
  // RED: each must be REJECTED. Three separate rows — a fixture for one is
  // defeated by a green that special-cases that single leading character.
  it('RED: a bare relative path /docs is rejected, not linked against our own origin', async () => {
    const contentArea = await applyLinkUrl('/docs')

    expectRejected(contentArea)
  })

  it('RED: a bare fragment #anchor is rejected, not linked against our own origin', async () => {
    const contentArea = await applyLinkUrl('#anchor')

    expectRejected(contentArea)
  })

  it('RED: a bare query ?q=1 is rejected, not linked against our own origin', async () => {
    const contentArea = await applyLinkUrl('?q=1')

    expectRejected(contentArea)
  })

  // \S* PINNED BY A TEST, not only by the comment above it. An enumeration like
  // `[\p{L}\p{N}\/%.@#?&=_~+:-]*` passes all 89 prior tests, so the "structural,
  // not enumerated" invariant is comment-forced and a future /refactor could
  // re-enumerate, stay green, and re-open the path hole. An emoji path char sits
  // outside any plausible enumeration. GREEN today and a regression guard: today
  // → `http://example.com/😀`, isAllowedUri true, `new URL()` OK, links. Must
  // survive whatever green adds (in particular a green that screens the HOST for
  // dead/deceptive chars per groups 1-2 must not also gut the legitimate path).
  it('an emoji in the path passes through as http://, keeping the path class structural not enumerated', async () => {
    const contentArea = await applyLinkUrl('example.com/\u{1F600}')

    expectSoleLink(contentArea, 'http://example.com/\u{1F600}')
  })

  // GROUP 5 — control char INSIDE the HOST_SHAPE branch (coverage-characterization,
  // LIVE not skip: the `\p{C}` screen in isUsable already exists). This is DISTINCT
  // from GROUP 2's soft hyphen (U+00AD, category Cf but NOT `\S` in a way that keeps
  // it in the host class — it misses HOST_SHAPE and reaches the FALLBACK). A
  // zero-width space (U+200B) is `\S` so it stays in the `([/?#]\S*)?` path segment
  // and MATCHES HOST_SHAPE → gets `http://`-prefixed → `isUsable` hits the
  // `/\p{C}/u` guard (normalizeHref.ts:50) FIRST, before `new URL()`, and returns
  // false → REJECT → alert. Exercises normalizeHref.ts:50 on the HOST_SHAPE path,
  // the branch no other test takes. TEETH proven by mutation-check on the RED commit
  // (delete line 50 → new URL('http://example.com/pa​th') does not throw →
  // isUsable true → the char ships as a live deceptive link → this test fails).
  it('a zero-width space in the path is rejected on the HOST_SHAPE branch, not shipped as a deceptive http:// link', async () => {
    const contentArea = await applyLinkUrl('example.com/pa​th')

    expectRejected(contentArea)
  })
})
