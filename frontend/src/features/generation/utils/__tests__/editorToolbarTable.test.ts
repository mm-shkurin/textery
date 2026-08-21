import { describe, expect, it, vi } from 'vitest'
import { TOOLBAR_ACTIONS } from '../../utils/editorToolbarActions'
import type { ToolbarRunAction } from '../../utils/toolbarAction'

// A chainable command recorder. Every Tiptap chain method returns the chain, so one Proxy stands in
// for the whole surface and records what was called — which is the only thing these actions do.
function fakeEditor(can: Record<string, boolean> = {}) {
  const calls: string[] = []
  const chain: Record<string, (...args: unknown[]) => unknown> = {}
  const proxy = new Proxy(chain, {
    get(_target, property: string) {
      if (property === 'run') return () => true
      return (...args: unknown[]) => {
        calls.push(args.length ? `${property}(${JSON.stringify(args[0])})` : property)
        return proxy
      }
    },
  })

  return {
    calls,
    editor: {
      chain: () => proxy,
      isActive: () => false,
      can: () => new Proxy({}, { get: (_t, name: string) => () => can[name] ?? false }),
    },
  }
}

function action(key: string): ToolbarRunAction {
  const found = TOOLBAR_ACTIONS.find((candidate) => candidate.key === key)
  if (found === undefined || found.run === undefined) {
    throw new Error(`no run-action named ${key}`)
  }
  return found
}

describe('editorToolbarActions — «вставить таблицу»', () => {
  it('inserts a 3×3 table with a header row', () => {
    const { calls, editor } = fakeEditor()

    action('table').run(editor as never)

    // The shape a user inserting a table almost always then builds, and the one that needs the
    // fewest presses to shrink if it is not.
    expect(calls).toContain('insertTable({"rows":3,"cols":3,"withHeaderRow":true})')
  })

  it.each([
    ['tableAddRow', 'addRowAfter'],
    ['tableAddColumn', 'addColumnAfter'],
    ['tableDelete', 'deleteTable'],
  ])('%s runs %s on the editor', (key, command) => {
    const { calls, editor } = fakeEditor()

    action(key).run(editor as never)

    expect(calls).toContain(command)
  })

  it.each(['tableAddRow', 'tableAddColumn', 'tableDelete'])(
    '%s is disabled outside a table',
    (key) => {
      const { editor } = fakeEditor()

      // Asked of the COMMAND rather than of `isActive('table')`: the command knows whether the
      // current selection admits the operation, which also covers a caret inside a nested
      // structure an isActive check would answer wrongly.
      expect(action(key).disabled?.(editor as never)).toBe(true)
    },
  )

  it.each([
    ['tableAddRow', 'addRowAfter'],
    ['tableAddColumn', 'addColumnAfter'],
    ['tableDelete', 'deleteTable'],
  ])('%s is enabled where the editor can run it', (key, command) => {
    const { editor } = fakeEditor({ [command]: true })

    expect(action(key).disabled?.(editor as never)).toBe(false)
  })

  it('offers insert unconditionally', () => {
    // Nothing to disable it against: a table can be inserted anywhere a paragraph can, and a
    // greyed-out insert would leave the user with no way to make the first one.
    expect(action('table').disabled).toBeUndefined()
  })

  it('marks the insert control active while the caret is inside a table', () => {
    const editor = { isActive: vi.fn().mockReturnValue(true) }

    expect(action('table').isActive(editor as never)).toBe(true)
    expect(editor.isActive).toHaveBeenCalledWith('table')
  })
})
