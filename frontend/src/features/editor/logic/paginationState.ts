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

export interface PaginationViewState {
  phase: PaginationPhase
  /** `null` while the count would be computed on substituted font metrics. */
  pageCount: number | null
  sheetSkeletonCount: number
  /**
   * Rail placeholder rows. A fixed design constant of the measuring surface, NOT a function of the
   * document — the rail shows the same three rows for a one-block document and a fifty-block one.
   */
  railSkeletonCount: number
  liveRegionRole: 'status' | null
  ariaBusy: boolean
  /** Status-bar copy. Product-defined per phase; the empty document reads "Страница 1 из 1" here. */
  statusText: string
  /** Copy on the measuring surface itself. Empty string in phases that render no such surface. */
  measuringMessage: string
}

export function derivePaginationState(input: PaginationInput): PaginationViewState {
  throw new Error('Not implemented')
}
