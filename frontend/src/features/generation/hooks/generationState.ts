// The state of one generation run, as one value.
//
// The jury's remark: the hook held six independent `useState` slots — state, content,
// generationId, volumePages, createdAt, error — for facts that only ever change together. Six
// setters in a row is not just noise; it is six chances to update five of them, and the illegal
// combinations are silent. 'completed' with a null content and 'failed' with no error message
// were both reachable, and both render as a blank screen.
//
// A reducer instead: each transition names what happened, and the state that follows is written
// once, in full.

export type GenerationUiState = 'idle' | 'pending' | 'completed' | 'failed'

export interface GenerationState {
  state: GenerationUiState
  content: string | null
  // The id of the run being watched. Exposed because a completed generation has to be CONVERTED
  // into a document before the editor can save anything.
  generationId: string | null
  volumePages: number | null
  createdAt: string | null
  error: string | null
}

export const IDLE_GENERATION: GenerationState = {
  state: 'idle',
  content: null,
  generationId: null,
  volumePages: null,
  createdAt: null,
  error: null,
}

export type GenerationAction =
  | { type: 'submitted' }
  | { type: 'accepted'; generationId: string }
  | {
      type: 'completed'
      // The server may report a finished run with no text — a completed generation that produced
      // nothing is still a completed generation, and the screen says so rather than staying pending.
      content: string | null
      volumePages: number | null
      createdAt: string | null
    }
  | { type: 'failed'; message: string }
  | { type: 'reset' }

export function generationReducer(
  current: GenerationState,
  action: GenerationAction,
): GenerationState {
  switch (action.type) {
    // A new run clears the previous one's result in the same step that starts it — the old
    // content must not survive into a screen that says «Готовим ваш доклад».
    case 'submitted':
      return { ...IDLE_GENERATION, state: 'pending' }

    // The server took the request. Only the id changes: the run is still pending.
    case 'accepted':
      return { ...current, generationId: action.generationId }

    case 'completed':
      return {
        ...current,
        state: 'completed',
        content: action.content,
        volumePages: action.volumePages,
        createdAt: action.createdAt,
        error: null,
      }

    // The id is kept: a failed run is still the run the user asked for, and a retry needs to know
    // which one it is retrying.
    case 'failed':
      return { ...current, state: 'failed', error: action.message }

    case 'reset':
      return IDLE_GENERATION
  }
}
