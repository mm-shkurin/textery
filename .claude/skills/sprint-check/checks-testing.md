# Criterion 4 — Test cases (0–2 points)

Worth as much as the other two development criteria combined, and the cheapest to
win: it grades **artifacts**, not code. Sprint 1 grades a test plan; sprints 2–8
grade test cases.

Mechanical probe: `DOC-TESTCASES` (the artifacts exist and are committed).
Everything else is a judgment item — a reviewer reads them and asks "could a stranger
execute this?".

## The jury's scale

| Score | Test cases (sprints 2–8) |
|---|---|
| 0 | Absent, or of no value — incomplete, abstract, beside the point |
| 1 | Present but formal, weakly structured; good enough only for a rough feature check |
| 2 | Clear, structured, covering the delivered functionality, understandable by anyone |

Sprint 1 grades the *plan*, i.e. readiness to test, not testing itself: 0 = missing or
generic phrases; 1 = draft with key sections but no detail, prioritization, or
scenarios; 2 = goals, approaches, bug-handling process, and candidate scenarios.

## What each case must carry

A case scoring 2 has every one of these, filled with concrete values:

| Field | Failure mode that costs the point |
|---|---|
| Identifier | Unnumbered cases cannot be referenced in a bug report |
| Title | "Check login" — states the object, not the outcome under test |
| Description | Missing, so the reason the case exists is unknown |
| Preconditions | Assumed rather than stated ("user is registered" with no account named) |
| Test data | Placeholders instead of actual values a tester can type |
| Steps | Vague verbs ("go to the page") instead of one action per numbered step |
| Expected result | Written as "works correctly" instead of the exact observable outcome |
| Status | No pass/fail column, so the run leaves no record |

## Checks

| Item | What is checked | Lane |
|---|---|---|
| Committed | Cases live in the graded repository, pushed to the release branch — not on a local disk, not in a chat, not in a tool the jury cannot open | `DOC-TESTCASES` |
| Coverage | Every requirement delivered this sprint has at least one case; the jury asks for minimal coverage of all requirements, not volume | judgment |
| Structure | Every field above present, per case, in a consistent template | judgment |
| Concreteness | Real data and exact expected results — a stranger can execute the case without asking a question | judgment |
| Traceability | Cases reference the story/requirement they cover | judgment |
| Currency | Cases match the functionality actually delivered this sprint, not last sprint's | judgment |

## Known state (2026-08-14)

The repository has no committed test artifacts: `Testing/` exists but is **untracked**,
and no test-case or test-plan file appears in `git ls-files`. Against this criterion
that is a 0 — the work is invisible to a jury that only reads GitVerse. Committing
existing material to the graded repository is the highest-value fix available.
