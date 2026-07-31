"""Spec-fixed literals every AI-edit scenario shares, in one place.

Vocabulary only — no client, no HTTP, no assertions, and no dependency on any seed,
probe or assertion module. It exists so the scenarios can agree on a value without one
of them importing another's assertion module for it: 1.3 was reaching into 1.1's
`ai_edit_guard_assertions` for `EMPTY_PAGE`, and 1.3's revision *seed* was importing its
own expectations module for the revision numbers — both the wrong direction.

The lifecycle states live in `ai_edit_edit_states`, the endpoint names in
`ai_edit_endpoints`, and the HTTP codes in `ai_edit_http_status`; this is the rest.
"""

# MessagePage / RevisionPage are `{items, next_cursor}`. `next_cursor` is null on the
# last page, and an empty page is a last page — so the whole page is pinned, not just
# `items`, or an extra disclosing field would slip through unasserted.
EMPTY_PAGE = {"items": [], "next_cursor": None}

# documents_revisions_list.yaml: the FIRST mutation of a never-edited document writes
# TWO revisions in one transaction — revision 1 carrying the pre-mutation content with
# source `manual`, then revision 2 carrying the result. So one applied AI edit on a
# freshly created document records revision 2 and leaves the document at version 2.
#
# The seeded number is therefore EXACTLY 2, never ">= 1": accepting 1 would accept a
# backend that wrote only the baseline and never applied the edit at all, and the
# cross-document refusal would then be trivially correct for the wrong reason.
BASELINE_REVISION_NUMBER = 1
SEEDED_REVISION_NUMBER = 2
VERSION_AFTER_ONE_AI_EDIT = 2
