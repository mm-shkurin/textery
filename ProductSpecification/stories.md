# In Progress

<!-- Track story progress across phases. Update as work proceeds. -->

| #  | Story                         | Spec | Back | Intg | Front | Sec | Load | Infra | Tests | %  |
|----|-------------------------------|------|------|------|-----|-------|------|-------|-------|----|
| 1  | Auto-generate: доклад          | ✅   | 🔧   | —    | 🔧   | —     | —    | —     | 12/74 | 16% |
| 7  | Authorization (email+password w/ mocked code, Yandex ID, VK ID) | · | · | · | · | · | · | · | · | · |

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
| 5  | Manual input mode (non-AI document creation) |      |      |      |     |       |      |       |       |    |
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
| 12 | History (list/search/filter)           |      |      |      |     |       |      |       |       |    |
| 13 | Profile management                     |      |      |      |     |       |      |       |       |    |
| 14 | Analytics Event Tracking                |      |      |      |     |       |      |       |       |    |
| 15 | Funnels & Reports (CSV export)          |      |      |      |     |       |      |       |       |    |

# Done

| #  | Story                         | Spec | Back | Intg | Front | Sec | Load | Infra | Tests | %       |
|----|-------------------------------|------|------|------|-----|-------|------|-------|---------|---------|
