/**
 * The editor's pre-layout state machine.
 *
 * Pagination is measured by the browser, but the DECISION of what the editor shows before the
 * measurement is trustworthy is pure: it depends on whether the document font has resolved, not on
 * any geometry. jsdom reports every element as zero-height, so this module is where scenario 1.1's
 * claim can be pinned at all — the geometric half lives in the Selenium leg.
 *
 * Vocabulary is the one `red-selenium` established (`pagination_measuring_locators.py`): a skeleton
 * sheet, exactly three rail skeleton rows, `role="status"` + `aria-busy="true"`, and no page count.
 */

export type DocumentFontStatus = 'pending' | 'resolved' | 'failed'

export interface PaginationInput {
  /** Readiness of the bundled document webfont, read from `document.fonts`. */
  fontStatus: DocumentFontStatus
  /** Measured heights of the document's blocks, in CSS pixels. Supplied by the caller. */
  blockHeights: number[]
  /** Height available for content on one sheet, in CSS pixels. */
  usableContentHeight: number
}

export type PaginationPhase = 'measuring' | 'laid-out' | 'error'

/**
 * One field per rendered node, and each fact held ONCE.
 *
 * `red-selenium` models the status bar as two separate nodes — `pagination-status` carries the
 * pagination phase's prose, `page-count` carries "Страница N из M" — and
 * `pagination_measuring_statements.py` names the failure that split exists to catch: a missing
 * `page-count` node with a status bar already reading "Страница 1 из 1" satisfies a pure absence
 * check while telling the user a page count in prose. So the count is carried by `pageCount` as a
 * NUMBER and by nothing else; no string field in this state may spell it out. The mockups agree —
 * `02-measuring.html:73` reads "Расчёт страниц…" with the count's slot holding only the sheet
 * geometry, while `01-editor-paginated.html:96` puts "Страница 1 из 3" in that other slot.
 *
 * The doc comment on each string field names the `data-testid` it is the text of, because that
 * mapping is the thing a pure test cannot assert and green must not be free to invent.
 */
export interface PaginationViewState {
  phase: PaginationPhase
  /**
   * The page count, as a number, for the `page-count` node to render. `null` while the count would
   * be computed on substituted font metrics — which is also the state in which that node is not
   * rendered at all.
   */
  pageCount: number | null
  sheetSkeletonCount: number
  /**
   * Rail placeholder rows. A fixed design constant of the measuring surface, NOT a function of the
   * document — the rail shows the same three rows for a one-block document and a fifty-block one.
   */
  railSkeletonCount: number
  /**
   * `null` in phases that render no live region — deliberately NOT a `'none'` member: `role="none"`
   * is a real ARIA role (the synonym of `presentation`) that STRIPS an element's semantics. A
   * consumer writing `role={state.liveRegionRole}` renders nothing for `null` and actively
   * suppresses semantics for `'none'`, so the absent case has to stay unrepresentable as a role.
   */
  liveRegionRole: 'status' | null
  ariaBusy: boolean
  /**
   * Text of the `pagination-status` node — the status bar's PHASE prose, never its page count.
   * Product-defined per phase: "Расчёт страниц…" while measuring. Empty string in phases that
   * contribute no such prose, including the laid-out one, where the only thing pagination has to
   * say is the count and the count is `pageCount` rendered by `page-count`. A value like
   * "Страница 1 из 1" here would put the count in prose behind the absence check that is supposed
   * to forbid it.
   */
  paginationStatusText: string
  /**
   * Text of the `pagination-measuring-message` node, on the measuring surface itself. Empty string
   * in phases that render no such surface.
   */
  measuringMessage: string
}

export function derivePaginationState(input: PaginationInput): PaginationViewState {
  throw new Error('Not implemented')
}
