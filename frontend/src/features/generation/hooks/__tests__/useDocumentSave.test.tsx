import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import type { Editor } from '@tiptap/react'
import * as documentApi from '../../api/documentApi'
import type { SaveDocumentResult } from '../../api/documentApi'
import { useDocumentSave } from '../useDocumentSave'
import { partialDouble } from '../../../../test/doubles'

// useDocumentSave pulls only saveDocument from documentApi at runtime; an ES module namespace is
// frozen, so the mock is declared via an explicit factory naming that single symbol.
vi.mock('../../api/documentApi', () => ({
  saveDocument: vi.fn(),
}))

// A minimal Tiptap surface: performSave reads getHTML() to capture what it sends and would call
// commands.setContent only when the server's content differs from what was sent (it never does
// here). Cast because the real Editor is far larger than these two members.
function fakeEditor(html = '<p>x</p>'): Editor {
  return partialDouble<Editor>({
    getHTML: () => html,
    commands: { setContent: vi.fn() },
  })
}

function renderSave(overrides: { documentId: string | null; editor: Editor | null }) {
  return renderHook(() =>
    useDocumentSave({
      documentId: overrides.documentId,
      editor: overrides.editor,
      onSaved: vi.fn(),
      onDirty: vi.fn(),
    }),
  )
}

describe('useDocumentSave', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Guard A — useDocumentSave.ts:155 (public save() null-guard true-branch). Called before init
  // has wired documentId/editor, save() must resolve to a no-op — there is nothing to persist and
  // saveDocument must never be reached with a missing id.
  it('resolves without calling saveDocument when documentId is null', async () => {
    const { result } = renderSave({ documentId: null, editor: fakeEditor() })

    await expect(result.current.save()).resolves.toBeUndefined()
    expect(documentApi.saveDocument).not.toHaveBeenCalled()
  })

  it('resolves without calling saveDocument when the editor is null', async () => {
    const { result } = renderSave({ documentId: 'doc-1', editor: null })

    await expect(result.current.save()).resolves.toBeUndefined()
    expect(documentApi.saveDocument).not.toHaveBeenCalled()
  })

  // Guard B — useDocumentSave.ts:160 (`return inFlightRef.current ?? Promise.resolve()`). A second
  // save() while one is in-flight must return the LIVE in-flight chain, so an awaiter waits for the
  // real persistence to settle — not an already-resolved promise. Resolving the single deferred
  // must settle BOTH the first and second awaiters.
  it('returns the live in-flight chain for a second save so both awaiters settle only after persistence resolves', async () => {
    let resolveSave: (value: SaveDocumentResult) => void = () => {}
    vi.mocked(documentApi.saveDocument).mockReturnValue(
      new Promise<SaveDocumentResult>((resolve) => {
        resolveSave = resolve
      }),
    )
    const { result } = renderSave({ documentId: 'doc-1', editor: fakeEditor() })

    const settled: string[] = []
    let first: Promise<void> = Promise.resolve()
    let second: Promise<void> = Promise.resolve()
    act(() => {
      first = result.current.save().then(() => {
        settled.push('first')
      })
      second = result.current.save().then(() => {
        settled.push('second')
      })
    })

    // Drain every already-queued microtask. Taken synchronously right after act(), a "nothing
    // settled" check is vacuous — no .then has had a turn yet, so it passes even for the bug it
    // claims to rule out. After a full drain it becomes a real discriminator: a correct second
    // save() returns the LIVE pending chain so nothing settles, while a buggy one returning an
    // already-resolved promise would run its .then here and push 'second'.
    await act(async () => {
      await Promise.resolve()
    })

    // Two save() calls, ONE real persistence round trip — the second folded into the in-flight
    // chain rather than starting its own. Neither awaiter has settled: the chain is unresolved.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(settled).toEqual([])

    resolveSave({ status: 'draft', content: '<p>x</p>', version: 2 })
    await act(async () => {
      await Promise.all([first, second])
    })

    // Resolving the single deferred settled BOTH — proving the 2nd save() awaited the LIVE chain,
    // not an already-resolved promise.
    expect(settled).toEqual(['first', 'second'])
  })
})
