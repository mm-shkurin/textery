# In Progress

<!-- Track story progress across phases. Update as work proceeds. -->

| #  | Story                         | Spec | Back | Intg | Front | Sec | Load | Infra | Tests | %  |
|----|-------------------------------|------|------|------|-----|-------|------|-------|-------|----|
| 1  | Auto-generate: доклад          | ✅   | 🔧   | —    | 🔧   | —     | —    | —     | 12/74 | 16% |
| 5  | Manual input mode (non-AI document creation) | ✅ | 🔧 | — | 🔧 | 🔧 | — | — | 0/40 | 0% |
| 7  | Authorization (email+password w/ mocked code, Yandex ID, VK ID) | ✅ | 🔧 | — | ✅ | 🔧     | —    | —     | 35/63 | 56% |
| 16 | OAuth sign-in: VK ID + Yandex ID (frontend-first, backend WIP) | ✅ | · | · | 🔧 | · | n/a | · | 4/13 | 31% |

# Backlog — Core sequence (build order, decided 2026-07-06)

Value-first order: prove the generation slice end-to-end for one document type before
anything else, then widen. **#1 must ship first.** #2–#4 (the other three document
types) may run in any order relative to each other and may interleave with #5–#8 (e.g.
#7 auth can land between #1 and #2) — the only hard constraint is #1 before all of them.

| #  | Story                                    | Spec | Back | Intg | Front | Sec | Load | Infra | Tests | %  |
|----|-------------------------------------------|------|------|------|-----|-------|------|-------|-------|----|
| 2  | Auto-generate: эссе                       |      |      |      |     |       |      |       |       |    |
| 3  | Auto-generate: сочинение                  |      |      |      |     |       |      |       |       |    |
| 4  | Auto-generate: реферат                    |      |      |      |     |       |      |       |       |    |
| 6  | Model switching (per-tariff AI model choice) |      |      |      |     |       |      |       |       |    |
| 8  | Billing (tariffs + mocked subscription payment) |      |      |      |     |       |      |       |       |    |

# Backlog — layered on top later (not yet ordered)

<!-- Remaining scope from .memory-bank/комплект продуктовой архитектуры.txt not covered
     by the 8 core stories above. -->

| #  | Story                                | Spec | Back | Intg | Front | Sec | Load | Infra | Tests | %  |
|----|----------------------------------------|------|------|------|-----|-------|------|-------|-------|----|
| 9  | Landing & Marketing                    |      |      |      |     |       |      |       |       |    |
| 10 | Text Editor polish (formatting, autosave) |      |      |      |     |       |      |       |       |    |
| 11 | Document Management (rename/delete/duplicate) |      |      |      |     |       |      |       |       |    |
| 12 | History (list/search/filter) — see note |      |      |      |     |       |      |       |       |    |
| 13 | Profile management                     |      |      |      |     |       |      |       |       |    |
| 14 | Analytics Event Tracking                |      |      |      |     |       |      |       |       |    |
| 15 | Funnels & Reports (CSV export)          |      |      |      |     |       |      |       |       |    |

**Note on #12 (History).** Its row stays all-blank — there is no story folder, no
interview, no spec, no test-spec — but part of its backend already exists, shipped
2026-07-17 outside the story lifecycle at the user's direction
(`feat: owner-scoped history for generations and documents`):

- `GET /api/v1/generations` and `GET /api/v1/documents` — the caller's own history,
  Bearer-required, owner-scoped in SQL, keyset-paginated, summary projection (no
  content). Contracts: `api-specs/generations_list.yaml`, `api-specs/documents_list.yaml`.
- Covered by unit, adapter and DB-level tests, and verified end to end against the
  running container. Not covered by an acceptance test — see the same gap named in
  `tasks/done/4-bug-generations-auth/progress.md`.

What #12 still owns: search, filter, titles, and whatever the interview decides. The row
is blank rather than 🔧 deliberately — blank means "no story work has started", which is
true; the endpoints arrived as feature plumbing, not as story #12's backend phase, and
marking them 🔧 would claim a spec and scenarios that do not exist.

# Done

| #  | Story                         | Spec | Back | Intg | Front | Sec | Load | Infra | Tests | %       |
|----|-------------------------------|------|------|------|-----|-------|------|-------|---------|---------|
