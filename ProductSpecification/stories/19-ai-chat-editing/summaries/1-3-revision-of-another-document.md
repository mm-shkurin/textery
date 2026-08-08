# Scenario 1.3: A revision belonging to another document of the same owner is not found

## red-acceptance (2026-07-31)

**Surprise:** The first mutation of a never-edited document writes **two** revision rows in one transaction — revision 1 carrying the pre-mutation content with source `manual`, then revision 2 carrying the result.
**Why:** `documents_revisions_list.yaml` specifies the baseline row so history is complete from the document's original state, not from its first AI edit.
**Impact:** Any seed that asserts `revision_number >= 1` accepts a backend that wrote only the baseline and never applied the edit; a seeded AI revision is number 2, and `changed: true` is what distinguishes the two.

## red-usecase (2026-08-08)

**Mistake:** Taking the ADR's "`_log_refusal` is shared with `resolve_owned_edit`, not copied" literally, by sharing the log call itself.
**Why wrong:** Scenario 1.2 pins its own logger name and message as test-side literals, and tests are read-only in GREEN — a shared line or logger breaks them.
**Correct location/approach:** Share the `extra`-building rule with logger and message as parameters, and assert the rule *between* the guards by reading both emitted records.

## green-usecase (2026-08-08)

**Quirk:** The deployed application configures logging nowhere, so `document_edit.*` inherits WARNING with no handler and every INFO refusal record both guards emit is dropped in production.
**Where:** `backend/application/src/app/main.py` — `import logging` and `getLogger(__name__)`, no `basicConfig` or `dictConfig`.
**Implication:** Any usecase reasoning about an audit or attribution log is reasoning about a channel with no receiver until the app configures one; test recorders call `setLevel(INFO)` and attach their own handler, so no test can observe the gap.

**Quirk:** Folding per-module `logger.info` calls into one shared helper silently moves every record's `filename`/`lineno`/`funcName` onto the helper unless it passes `stacklevel=2`.
**Where:** `backend/usecase/src/document_edit/refusal_log.py`.
**Implication:** No test catches it — the cross-guard shape check subtracts every standard `LogRecord` attribute before comparing — so any future log-helper extraction must set `stacklevel` deliberately.
