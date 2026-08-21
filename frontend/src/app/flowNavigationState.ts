import { documentTypeFromWire, type DocumentType } from '../shared/domain/documentTypes'

// 'auto' generates from a topic, 'manual' opens the editor. Both are real destinations, not a
// request flag — they are different screens. Story 18 dropped the mode-select modal, so on the
// create path `mode` is always 'auto'; 'manual' now survives only on the history-open path.
export type GenerationMode = 'auto' | 'manual'

export type Step = 'landing' | 'type' | 'form' | 'history'

// The four values are ONE position in the flow, not four independent switches: every transition
// below writes at least two of them, and any pair left out of step with the others is a screen
// the product does not have (a 'form' with no document type, an open document id on the landing).
// Holding them as one value is what makes those combinations unwritable.
export interface FlowState {
  step: Step
  documentType: DocumentType | null
  mode: GenerationMode | null
  openDocumentId: string | null
}

export const INITIAL_FLOW_STATE: FlowState = {
  step: 'landing',
  documentType: null,
  mode: null,
  openDocumentId: null,
}

// Every move the flow can make, named for what the user did rather than for what it assigns.
export type FlowAction =
  | { type: 'closeToLanding' }
  | { type: 'backToLanding' }
  | { type: 'startCreation' }
  | { type: 'openHistory' }
  | { type: 'selectDocumentType'; documentType: DocumentType }
  | { type: 'openDocumentFromHistory'; documentId: string; wireType: string }
  | { type: 'backFromEditor' }

export function flowReducer(state: FlowState, action: FlowAction): FlowState {
  switch (action.type) {
    case 'closeToLanding':
      return INITIAL_FLOW_STATE
    // Only the step moves: the landing is reachable from a half-made selection the user may come
    // straight back to, unlike `closeToLanding`, which is an abandonment.
    case 'backToLanding':
      return { ...state, step: 'landing' }
    case 'startCreation':
      return { ...state, step: 'type' }
    case 'openHistory':
      return { ...state, step: 'history' }
    // Story 18 1.1: picking a type goes STRAIGHT to generation. The mode-select modal is gone, so
    // there is no intermediate 'mode' step and no mode to choose — the create path is always
    // 'auto'. `openDocumentId` stays null, which is what tells the workspace to POST a new
    // generation rather than GET an existing document.
    case 'selectDocumentType':
      return {
        step: 'form',
        documentType: action.documentType,
        mode: 'auto',
        openDocumentId: null,
      }
    // The row carries the wire's Cyrillic type; the app speaks its own. An unrecognised value (the
    // server added a type this build has never heard of) falls back to 'doklad' rather than
    // refusing to open the document over an unfamiliar label — the real content comes from the GET
    // either way.
    // NOTE: since scenario 1.1 threaded the type to the wire, `documentType` is no longer
    // display-only — `submitGeneration` puts it on a POST. The fabricated 'doklad' cannot reach the
    // wire today, because this path sets mode='manual' + openDocumentId and routes to ManualEditor,
    // and every route back to the create path passes through `selectDocumentType`. Any NEW path
    // into step='form' that skips it would inherit a silently fabricated wire value — thread a real
    // type instead.
    case 'openDocumentFromHistory':
      return {
        step: 'form',
        documentType: documentTypeFromWire(action.wireType) ?? 'doklad',
        mode: 'manual',
        openDocumentId: action.documentId,
      }
    // Back from the editor goes to the list of the user's own works — from BOTH paths, and the
    // generated one is the change here. It used to land on the type step, which renders the
    // "Создание документа" modal over the landing: someone who had just finished a доклад was
    // answered with a prompt to start another one, and the only route to the document they had
    // just saved was to dismiss that modal and then find "Мои работы" in the header. Two
    // non-obvious clicks away from the one thing they were most likely to want next.
    //
    // History is where the work they just did now IS (a completed generation becomes a Document),
    // so it is both the honest destination and a forward-reachable one — the CTA in the landing
    // header is still one click from here for anyone who did want to start again.
    case 'backFromEditor':
      return { ...state, step: 'history', mode: null, openDocumentId: null }
  }
}
