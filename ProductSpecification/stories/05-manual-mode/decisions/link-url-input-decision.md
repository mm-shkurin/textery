# Decision: Link URL input is an inline popover, not window.prompt

**Date**: 2026-07-16 **Scenarios**: 7.9

The `ToolbarAction.run: (editor) => void` contract discards `setLink`'s `false` return, so a rejected URL is indistinguishable from cancel; and with all Selenium steps `[S]` on this branch, jsdom is the only evidence available — but jsdom stubs `window.prompt`, so it cannot observe the blocking modal's focus/selection risk that is `prompt`'s whole downside.

| Rejected | Why |
|----------|-----|
| `window.prompt` MVP (the plan's suggestion, `jazzy-stirring-key.md` § 9) | Cheaper (~12 lines, no contract change), but its central risk is unverifiable by construction on this branch: the jsdom test passes whether or not a real browser collapses the ProseMirror selection. A green test structurally blind to the hazard it exists to catch. |
| `window.prompt` + `window.alert` on rejection | Buys the rejection signal but not the verifiability — same jsdom blindness, plus a crude modal-on-modal. |
| Escalate to `/architecture` | Trade-off is real but narrow (one control, one contract change); a full ADR discussion is not warranted beyond this record. |

**Chosen**: inline `LinkPopover` component anchored to the toolbar button — URL input, apply/cancel, and an inline rejection message. `ToolbarAction` gains a UI channel (the `disabled?(editor)` predicate added in 7.5 is the precedent for extending the contract rather than special-casing the renderer).

## Model

- `LinkPopover.tsx` — new; input + apply/cancel + inline error slot.
- `ToolbarAction` — gains an opt-in UI channel; `run(editor)` stays for the 16 existing click-only actions.
- `editorToolbarActions.ts` — new `link` entry, `testId: 'toolbar-link'`, `isActive: editor.isActive('link')`.
- `StarterKit.configure({ link: { openOnClick: false, autolink: false, linkOnPaste: false } })` — Link is **already registered** via StarterKit 3.27.4 (`@tiptap/extension-link` is a starter-kit dependency). Do **not** add a separate `Link` registration or a direct `package.json` dependency; that is the duplicate-extension mistake 7.7 made and removed.
- URL normalization lives in the popover's apply path: `defaultProtocol: 'http'` does **not** normalize on the `setLink` path (it is passed only to `isAllowedUri` and the linkify/autolink path, `extension-link/dist/index.js:365-376` stores `attributes` verbatim). A bare host must be prefixed explicitly or it serializes as a relative URL against the app's own origin.

## Edge Cases

| Case | Behavior |
|------|----------|
| Cancel | Document byte-identical; an existing link survives. |
| Empty input | `unsetLink` — removes the link, text survives. |
| Whitespace-only input | Treated as empty (Link's default `validate: (url) => !!url` would otherwise accept `'   '`). |
| Disallowed protocol (`javascript:`, typo'd `htp://x`) | Rejected with a visible inline message. Never silently nothing. |
| Bare host (`example.com`) | Normalized to `http://example.com` before `setLink`. |
| Collapsed cursor outside any link | No-op — `extendMarkRange('link')` has empty scope; zero characters linked. |
| Stored `<a>` with a disallowed href arriving via `setContent` | Mark not applied (Tiptap `getAttrs` returns false); text survives, href is dropped and the next save persists that drop. Accepted: the allowlist covers http/https/ftp/mailto/tel/callto/sms/cid/xmpp, so a legitimate-but-dropped protocol is not a realistic case. |

## Knowingly unverified on this branch

Not gaps to close in 7.9 — record so no one reads the green suite as more than it is:

- **Client↔server round-trip.** The `*.parseHTML` test is `renderHTML → parseHTML` inside one jsdom process. If the backend sanitizes `target`/`rel`/`href`, every test stays green and the reload diverges. Verified only when a live backend reaches this branch and 7.9's `green-selenium` runs.
- **The href allowlist is client-side UX, not enforcement.** A crafted `PUT` bypasses Tiptap entirely. Whether the server independently allowlists href protocols is unowned and unverified here.
- **No href length bound.** `isAllowedUri` gates protocol, not magnitude; a multi-MB href passes. The authoritative bound is the server's.
- **No exit guard exists at all** — `beforeunload`/blocker: zero hits in `frontend/src`. `openOnClick: false` is therefore the sole barrier between an anchor click and total content loss, on a page whose save-error banner already falsely claims local persistence (see `carryover.md`). This ADR requires a test pinning `openOnClick: false`; the missing exit guard itself is out of 7.9's scope.
