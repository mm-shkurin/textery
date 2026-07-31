# Scenario 1.3: A revision belonging to another document of the same owner is not found

## red-acceptance (2026-07-31)

**Surprise:** The first mutation of a never-edited document writes **two** revision rows in one transaction — revision 1 carrying the pre-mutation content with source `manual`, then revision 2 carrying the result.
**Why:** `documents_revisions_list.yaml` specifies the baseline row so history is complete from the document's original state, not from its first AI edit.
**Impact:** Any seed that asserts `revision_number >= 1` accepts a backend that wrote only the baseline and never applied the edit; a seeded AI revision is number 2, and `changed: true` is what distinguishes the two.
