## discussion (2026-07-14)

**Decision:** Use Tiptap (`@tiptap/react` + `@tiptap/starter-kit`, ProseMirror-based) for the rich-text editor powering scenarios 3.1/3.2, rather than a hand-rolled contentEditable + `document.execCommand` implementation.
**Why:** Tiptap ships ready extensions for the required controls (Bold, Italic, Heading, BulletList/OrderedList) and `editor.isActive('bold')`-style state queries that map directly onto "highlight the active toolbar button at the cursor position" — avoiding the cross-browser inconsistency of `execCommand` and the extra code a bespoke solution would need for cursor-aware state.
**Where applied:** `ManualEditor.tsx`'s toolbar/content-area (currently static placeholders) and `frontend/package.json` dependencies — will be wired in during scenario 3.1's `red-frontend`/`green-frontend` steps.

## red-selenium (2026-07-14)

**Expected:** TimeoutException from `assert_selected_text_is_bold` waiting on `.me-content-area strong` (assumed `send_keys` on the placeholder div would silently no-op).
**Actual:** ElementNotInteractableException raised earlier, directly from `content_area.send_keys(text)` inside `type_text_in_editor`.
**Why:** `.me-content-area` has no `contenteditable` attribute and isn't a form control, so WebDriver refuses to send keys to it at all — the failure surfaces one call earlier than predicted, but the root cause (no real editable surface yet) is the same.
**Resolution:** Corrected the prediction record; no test/setup change needed since the actual failure still confirms the expected gap.
