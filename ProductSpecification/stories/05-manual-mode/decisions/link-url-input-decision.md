# Decision: Link URL input is an inline popover, not window.prompt

**Date**: 2026-07-16 **Scenarios**: 7.9

The `ToolbarAction.run: (editor) => void` contract discards `setLink`'s `false` return, so a rejected URL is indistinguishable from cancel; and with all Selenium steps `[S]` on this branch, jsdom is the only evidence available — but jsdom stubs `window.prompt`, so it cannot observe the blocking modal's focus/selection risk that is `prompt`'s whole downside.

| Rejected | Why |
|----------|-----|
| `window.prompt` MVP (the plan's suggestion, `jazzy-stirring-key.md` § 9) | Cheaper (~12 lines, no contract change), but its central risk is unverifiable by construction on this branch: the jsdom test passes whether or not a real browser collapses the ProseMirror selection. A green test structurally blind to the hazard it exists to catch. |
| `window.prompt` + `window.alert` on rejection | Buys the rejection signal but not the verifiability — same jsdom blindness, plus a crude modal-on-modal. |
| Escalate to `/architecture` | Trade-off is real but narrow (one control, one contract change); a full ADR discussion is not warranted beyond this record. |

**Chosen**: inline `LinkPopover` component anchored to the toolbar button — URL input, apply/cancel, and an inline rejection message. `ToolbarAction` gains a UI channel (the `disabled?(editor)` predicate added in 7.5 is the precedent for extending the contract rather than special-casing the renderer). The field is **optional**, so the other 17 click-only actions are structurally untouched.

## Model

- `LinkPopover.tsx` — new; input + apply/cancel + inline error slot.
- `ToolbarAction` — gains an opt-in UI channel; `run(editor)` stays for the 16 existing click-only actions.
- `editorToolbarActions.ts` — new `link` entry, `testId: 'toolbar-link'`, `isActive: editor.isActive('link')`.
- `StarterKit.configure({ link: { openOnClick: false, autolink: false, linkOnPaste: false } })` — Link is **already registered** via StarterKit 3.27.4 (`@tiptap/extension-link` is a starter-kit dependency). Do **not** add a separate `Link` registration or a direct `package.json` dependency; that is the duplicate-extension mistake 7.7 made and removed.
- URL normalization lives in the popover's apply path: `defaultProtocol: 'http'` does **not** normalize on the `setLink` path (it is passed only to `isAllowedUri` and the linkify/autolink path, `extension-link/dist/index.js:365-376` stores `attributes` verbatim). A bare host must be prefixed explicitly or it serializes as a relative URL against the app's own origin.
- **The apply path is `extendMarkRange('link').setLink({ href })`, not bare `setLink`** — added after premortem caught that this Model section never named it (it appeared only in the "collapsed cursor outside any link" edge-case row, which made it look incidental). Without it, editing an existing link is broken in two ways a fresh-selection test cannot see: a collapsed cursor inside a link writes a stored mark instead of changing the href (so the old URL ships and the next typed character becomes a *second* link), and a partial selection inside a link splits the anchor into three. Editing an existing link is contemplated elsewhere in this ADR — the Cancel row promises "an existing link survives" — so its apply path is not optional.

## Edge Cases

| Case | Behavior |
|------|----------|
| Cancel | Document byte-identical; an existing link survives. |
| Empty input | `unsetLink` — removes the link, text survives. |
| Whitespace-only input | Trim first, then treat as empty → `unsetLink`. **Corrected twice — read the second correction, the first was itself the same error class.** The original row said "treated as empty (Link's default `validate: (url) => !!url` would otherwise accept `'   '`)". The first correction said `validate` is deprecated and `onCreate` copies it into `shouldAutoLink` (`:244-250`), which governs only the autolink path. **That mechanism does not execute either:** the line is guarded by `if (this.options.validate && !this.options.shouldAutoLink)` (`:244`), and `shouldAutoLink` has a default implementation in `addOptions` (`:278-292`) that is always truthy — so the copy never runs under any config here, and the deprecation warning never fires. `validate` is inert for a *stronger* reason than stated. The conclusion is unchanged and survives a fortiori: the real gate is `isAllowedUri`, which strips unicode whitespace (`:231`) leaving `''`, matching nothing (every alternative needs ≥1 char) → `setLink` returns **false** (`:369`). Untrimmed whitespace is *rejected*, not treated as empty; without an explicit trim the visitor gets a rejection message for pressing space — hence trim-then-unset. |
| Disallowed protocol (`javascript:`, typo'd `htp://x`) | Rejected with a visible inline message. Never silently nothing. |
| Bare host (`example.com`) | Normalized to `http://example.com` before `setLink`. |
| Collapsed cursor outside any link | No new characters linked, but **not** a true no-op: `setLink` → `setMark` on an empty selection adds a **stored mark**, so the next typed character becomes a link. Pin this rather than asserting "nothing happens" — the original row claimed a no-op, which is only true at that instant. |
| Stored `<a>` with a disallowed href arriving via `setContent` | Mark not applied (Tiptap `getAttrs` returns false); text survives, href is dropped and the next save persists that drop. Accepted: the allowlist covers http/https/**ftps**/ftp/mailto/tel/callto/sms/cid/xmpp (`:212-222`), so a legitimate-but-dropped protocol is not a realistic case. |
| Typing at the end of a link | `autolink: false` also makes the link mark **non-inclusive** — `inclusive() { return this.options.autolink }` (`:261-263`). So typing immediately after a link does not extend it. A consequence of the config choice, not an independent decision; pin it so the coupling is visible. |

## Knowingly unverified on this branch

Not gaps to close in 7.9 — record so no one reads the green suite as more than it is:

- **Client↔server round-trip.** The `*.parseHTML` test is `renderHTML → parseHTML` inside one jsdom process. If the backend sanitizes `target`/`rel`/`href`, every test stays green and the reload diverges. Verified only when a live backend reaches this branch and 7.9's `green-selenium` runs.
- **The href allowlist is client-side UX, not enforcement.** A crafted `PUT` bypasses Tiptap entirely. Whether the server independently allowlists href protocols is unowned and unverified here.
- **No href length bound.** `isAllowedUri` gates protocol, not magnitude; a multi-MB href passes. The authoritative bound is the server's.
- **No exit guard exists at all** — `beforeunload`/blocker: zero hits in `frontend/src`. `openOnClick: false` is therefore the sole barrier between an anchor click and total content loss, on a page whose save-error banner already falsely claims local persistence (see `carryover.md`). This ADR requires a test pinning `openOnClick: false`; the missing exit guard itself is out of 7.9's scope.
- **The popover's own hazards — added after premortem, and they blunt this ADR's central argument.** The popover was chosen partly because it "puts the mechanism under jsdom's actual reach". That is true of the *rejection signal* only. jsdom has no layout engine, and `.me-editor-shell` carries `overflow: hidden` (`ManualEditor.css:74`) — an ancestor of the toolbar. So placement, clipping, z-index stacking, and narrow viewports are exactly as unverifiable as `window.prompt`'s focus behaviour was: **the decision relocated the blind spot rather than removing it**. Recorded here so the green suite is not read as covering it. Also unpinned by the edge-case table above and left to `red-frontend` to decide deliberately: Escape and click-outside disposition of half-typed input (the table has only "Cancel"), and whether the apply path uses `.chain().focus()` — a popover `<input>` blurs the contenteditable exactly as `prompt` does and holds focus longer; the existing 17 buttons prove `.focus()` restores selection, but nothing here *requires* it and jsdom passes either way.
