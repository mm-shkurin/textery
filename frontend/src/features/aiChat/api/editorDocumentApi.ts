// STUB — behaviourally empty on purpose (TDD red, Story 19 Frontend Scenario 0.1).
//
// It exists so that the static imports and the `vi.mock` path in
// `components/__tests__/DocumentEditorPage.notFound.test.tsx` resolve: Vite's import analysis
// resolves both at transform time, even under `describe.skip`, so a reference to a module that
// does not exist crashes collection instead of failing a test.
//
// The real body lands in `red-frontend-api` / `green-frontend-api`, which owns mapping the
// shared 404 body (`endpoints.md`: "All seven endpoints share one 404 body") onto
// DocumentNotFoundError. An absent document and another account's document are indistinguishable
// from the client — the same 404 answers both — so ONE error type covers both halves of the
// scenario's Given.
export interface EditorDocument {
  documentId: string
  content: string
  version: number
}

export class DocumentNotFoundError extends Error {
  constructor() {
    super('Документ не найден')
    this.name = 'DocumentNotFoundError'
  }
}

export async function loadEditorDocument(documentId: string): Promise<EditorDocument> {
  throw new Error(`Not implemented: loadEditorDocument(${documentId})`)
}
