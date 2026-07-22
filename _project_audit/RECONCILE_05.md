# RECONCILE — Story 5 (Manual input mode)

Phase A classification. Written 2026-07-20 (reconcile session, read-only vs code).
Legend: **legit** / **deferred** / **stale** (see RECONCILE_07.md header).

## Acceptance-test skip (`@pytest.mark.skip`)

| file:line | type | reason today | what to do | layer |
|---|---|---|---|---|
| `acceptance/tests/frontend/generation/test_manual_editor_acceptance.py:45` | **stale** | Skip claims `.me-content-area` is "a static placeholder div with no contenteditable attribute". FALSE: `ManualEditor.tsx:151-152` renders `<EditorContent editor={editor}/>` (TipTap) inside `.me-content-area`; unit tests `ManualEditor.formatting.test.tsx:39` and `ManualEditor.inlineCode.test.tsx:12` both assert `contentArea toHaveAttribute('contenteditable','true')`. The editable element is the ProseMirror div **inside** the wrapper. | Un-skip. Fix locator in `acceptance/statements/frontend/generation/manual_editor_statements.py:97 _focus_content_area` — `CONTENT_AREA` (line 18) targets the `.me-content-area` wrapper; `send_keys` must go to the inner contenteditable (`.me-content-area .ProseMirror` or `[contenteditable="true"]`). Then green against live app. | frontend |

## Backend tracking gap

| item | type | reason today | what to do | layer |
|---|---|---|---|---|
| No `progress-backend.md` in `ProductSpecification/stories/05-manual-mode/` | **deferred** | Backend/integration/security scenarios untracked. `stories.md` shows Story 5 Back=🔧, Sec=🔧, Tests 0/40. Backend adapters exist (`documents` usecase wired `main.py:119` list_documents) but no per-scenario TDD record. | Bootstrap `progress-backend.md` from `tests/{01_API,05_Security,06_Integration}_Tests.md`, then TDD per scenario (Phase C). | backend |

## Frontend progress `[S]` — the "backend unavailable" selenium legs (STALE cluster)

Skip reason `"backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against"` recurs across **~40** green-selenium / red-selenium / demo entries:
lines 61,71,72,75,81,82,85,91,92,95,101,102,105,111,112,115,121,122,125,131,132,135,141,142,156,162,163,166,176,177,180,188,189,194,206,207,210,218,219,224,236,237,242,271,272,275,287,288,587,736,737.

| type | reason today | what to do | layer |
|---|---|---|---|
| **stale** (the `green-selenium`/`red-selenium` subset) | The parallel-branch merges have landed (`git log`: Story 5 frontend + manual-mode backend merged into dev). Backend is now live-runnable (adapters `db/rest/security/generation_provider` present, `main.py` wires document usecases). The "no live app" justification is dead **once the stack is started**. These selenium legs were never executed against a real browser+backend. | With live stack up, run each `green-selenium` leg; those that pass → `[x]` with real e2e; those that fail → real gap → Phase C. Explicitly flagged owed by premortem at lines 81, 101–102 (4.2 queue), 158 (7.9 popover clipping). | frontend (needs live backend) |
| **legit** (the `demo` subset) | `demo` is visual-only, non-gating convention-skip; not a coverage gap. | none | frontend |

Note: distinguish within the cluster — `green-selenium`/`red-selenium` lines are **stale/deferred e2e legs** (backfill target); paired `demo` lines are **legit**.

## Frontend progress `[S]` — genuine no-gap (drop)

**legit** — no port / already-covered / no-RED-achievable coverage pins:
lines 36,37,46,47,56–60,68,69,77,78,79,98,99,108,109,119,128,129,139,159,160,169,170,183–186,201–204,213–216,227,228,245,246,278,279,560.
Client-side editor state (bold/formatting/cursor toolbar), reuse of scenario 1.2's ManualEditor build, born-green characterization pins (`horizontalRule.parseHTML`, `inlineCode.parseHTML`, toolbar-disabled). Verified samples against code; no action.

## Net backlog for Story 5

- **Phase B (stale, urgent):** un-skip `test_manual_editor_acceptance.py` + fix contenteditable locator.
- **Phase C (deferred):** bootstrap `progress-backend.md`; run all `green-selenium` legs against live stack (the "backend unavailable" reason is dead) and backfill real gaps.
- `demo` skips + client-side-state skips: **legit** — drop.
