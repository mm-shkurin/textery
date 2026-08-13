# How the sprint is actually graded

Source: the season's public criteria (last edited 2026-08-02). This file is what the
skill obeys; the checklists only say *what* is inspected.

## Stage 0 — the precondition gate (run before anything else)

The jury opens the sprint at **22:00 Friday (GMT+6)**. Before that moment:

1. **Deployed links must exist and work.** No links, links that do not open, or an
   app that does not start / does not function → **the entire sprint scores 0** and
   no criterion is graded at all. Nothing else in this skill can compensate for it.
2. **Every artifact must live in GitVerse.** Source, links, instructions, agreements,
   presentations — material hosted anywhere else (GitHub included) **is not graded**.
   Check each layer's `artifact_remote` in `probes/config.json` is pushed and current.
3. **The release branch must contain the sprint's work.** Code is graded from the
   release branch only (`main`/`master`/`release`) — not `dev`, not a feature branch.
   Day-to-day the skill runs against the working tree (same files, no ceremony); this
   gate is where the release refs are verified — see SKILL.md "Grading target".
4. **What was demoed must be in the code.** If the jury judges the code absent or not
   matching the demo, the repo receives the group's average score instead of its own.

Report the gate first, in this order, before any criterion score. A gate failure is
the only finding that matters that day.

## What the skill grades, and what it cannot

Technical aspect — 5 points:

| Part | Points | Covered here |
|---|---|---|
| Git repo + README + Wiki | 0–1 | `checks-git-docs.md` |
| Consistency, architectural style, formatting | 0–1 | `checks-consistency.md` |
| Code quality / code smells | 0–1 | `checks-smells.md` |
| Test cases (sprints 2–8) or test plan (sprint 1) | 0–2 | `checks-testing.md` |

Product aspect — 5 points (pitch 0–2, UX/UI 0–2, User Story Map delivery 0–1) is
**outside this skill**, with one exception: the User Story Map point asks whether
everything demoed actually works — that is the Stage 0 gate's live check.

An AI-assisted single-developer track is graded instead as one 0–3 score by the
auditor prompt (`auditor-prompt.md`) — that is exactly Stage A of this skill.

## Scoring

Per criterion, per repository:

- any regression item not PASS → **0**
- regressions clean, new findings present → **0.5**
- everything PASS or WAIVED → **1**

Several repositories (backend and frontend are separate GitVerse repos) → grade each
one on its own, then **average and round**. Never grade the monorepo as one unit; the
jury never sees it.

## Rounding

From sprint 5 onward, mathematical rounding — no automatic rounding up:

- prefer rounding up to the nearest whole number when the absolute difference between
  the two values is ≤ 2
- halves are allowed only as the result of that rule
- worked examples: 1 and 3 → **2**; 1 and 4 → **2.5**; 2 and 6 → **4**; 1 and 6 → **4**

State both repo scores and the rounded result; never present the rounded number alone.

## After the verdict

Appeals close **20:00 Monday** after the sprint. A finding the skill can disprove with
`file:line` evidence from the release branch is appeal material — collect such evidence
in the report rather than arguing from memory.
