---
name: sprint-check
description: Run the sprint self-audit — Stage A drives the AI-auditor loop (5–7 zero-bias iterations per layer, target >= 2.5/3.0) and Stage B replays the grader's manual checklist item by item, producing a verdict report. Use before a sprint deadline, after fixing grader remarks, or when the user mentions /sprint-check.
---

# /sprint-check — Self-Grade the Sprint

Three stages, always in this order. **Read `grading-rules.md` first** — it holds the
season's actual rules: the precondition gate, what is graded from where, scoring, and
rounding.

- **Stage 0 — the gate.** Deployed links open and the app works; every artifact is in
  GitVerse; the release branch carries the sprint's work. A gate failure means the
  sprint scores 0 regardless of code quality, so it is reported before anything else
  and nothing later can compensate for it.

  A failed gate **does not stop the run**. Stages A and B read files and history;
  they do not need a live stand, and blocking them would burn sprint time for
  nothing. The consequence of a failed gate is narrow and strict: the run may not
  present a score — every criterion result is reported as provisional, under the
  blocker — and fixing the gate is the top item of the report. Only an explicit
  instruction from the user stops the run.

Then:

- **Stage A — audit loop.** The reviewers' own prompt (`auditor-prompt.md`), run by a
  fresh zero-bias auditor agent per iteration, 5–7 iterations per layer, fixing
  between runs until the score holds at >= 2.5/3.0. Rules: `loop-rules.md`.
- **Stage B — manual check.** The graded checklist replayed item by item: mechanical
  probes from `probes/run.py` plus review agents for the judgment items. Produces
  the verdict report.

Stage A raises the score; Stage B proves the specific remarks the grader wrote are
gone. Neither replaces the other — Stage A's auditor is a generalist and will miss a
project-specific remark; Stage B cannot judge SRP.

## The pipeline

`/sprint-check` is the one command that runs everything. Scope decides *which*
directories it walks; nothing else about the sequence changes.

```
Stage 0  gate ──failed──▶ record the blocker, keep going
   │                      (a failed gate forbids claiming a score,
   │                       it does not forbid the work)
   ▼
Stage A  per layer, up to 7 iterations:
   audit (fresh zero-bias agent) ─▶ score + findings
        │ score >= 2.5 ─▶ confirmation audit ─▶ hold ─▶ next layer
        │ score <  2.5 ─▶ backlog ─▶ fix ─▶ atomic commit ─▶ build/lint/tests
        └────────────────────────── back to audit ◀────────┘
   every iteration appended to <layer>/AUDIT_LOG.md
   ▼
Stage B  manual checklist, once, after the loops settle:
   probes (mechanical) ‖ review agents (judgment)
   ─▶ score per criterion per repo ─▶ average + round
   ─▶ _project_audit/sprint-check-<date>-<scope>.md
```

Stage A raises the score; Stage B proves the graded remarks are gone. Stage B runs
last because a checklist over code that is still being rewritten is wasted work.

## Usage

- `/sprint-check` — whole repo: Stage A for every layer, then Stage B for everything
- `/sprint-check back` / `front` / `back,front` — same pipeline, only those layers
  (any layer name declared in `probes/config.json`)
- `/sprint-check --back` / `--front` — **one layer, end to end**, for a solo session
- `/sprint-check --stage b` — checklist only, no fixing (fast, before a deadline)
- `/sprint-check --stage a --front` — loop one layer, no checklist
- `/sprint-check git-docs | consistency | smells` — one Stage-B criterion
- `/sprint-check --fix` — Stage B may also apply mechanical fixes (see Fix Mode)
- `/sprint-check --release` — grade the pushed release refs instead of the working
  tree; run it before the deadline, not on every iteration (see Grading target)

## Scope and isolation

`--back` and `--front` are hard boundaries, not filters on the output. Two sessions
must be able to run them at the same time without colliding
(`CLAUDE.md`, File Ownership; `.memory-bank/steerings/development-conventions.md`
for worktrees). In a single-layer run:

| | `--back` | `--front` |
|---|---|---|
| Auditor working directory | `backend/` | `frontend/` |
| Files that may be edited | `backend/`, `acceptance/tests/backend/` | `frontend/`, `acceptance/tests/frontend/` |
| Probes | `run.py --layer back` | `run.py --layer front` |
| Checklist items | `*-B*` only | `*-F*` only |
| Score | that layer's `X/1` per criterion | same |
| Audit log | `backend/AUDIT_LOG.md` | `frontend/AUDIT_LOG.md` |
| Report | `_project_audit/sprint-check-<date>-back.md` | `…-front.md` |

Rules that follow from the boundary:

- The auditor prompt gets `<LAYER_DIR>` = that directory and **runs its commands
  inside it**, so its `find .`, `git log`, and README are the layer's own. Its score
  is that layer's score; never average the two, never quote the other layer's.
- Git-history checks are pathspec-scoped: `git log --oneline -- <layer>/`,
  `git ls-files <layer>/`. A bulk commit in the other layer is not this layer's finding.
- Shared files (root `README.md`, `infra/`, `ProductSpecification/stories.md`) are
  **read-only** in a single-layer run. If a finding lives there, it goes to
  `## Needs a task` with the owning layer named — do not edit it, the other session
  may be in it.
- A full run (`/sprint-check` with no layer flag) writes
  `_project_audit/sprint-check-<date>-full.md`, scores both layers separately in one
  report, and may edit shared files.
- `## Delta` compares against the previous report **of the same scope** — a `back`
  report is never diffed against a `full` one.

## Stage A — audit loop

Read `loop-rules.md` and follow it exactly. Per layer:

1. Dispatch a fresh `general-purpose` agent with `auditor-prompt.md` (substitute
   `<LAYER_DIR>`) and nothing about previous iterations.
2. Print its Score and finding list verbatim.
3. `>= 2.5` → one confirmation run, then stop. Below → fix, commit atomically, repeat.
4. Cap 7 iterations; append every iteration to `<layer>/AUDIT_LOG.md`.

In a full run both layers loop concurrently — disjoint directories, one auditor and
one `AUDIT_LOG.md` each, two independent scores.

## Stage B — manual checklist

Criteria files, one per graded criterion. Each is a catalogue of **defect classes**,
not a list of this project's files — the same checklist grades any repository:

| Criterion (grader wording) | Weight per repo | File | Probe categories |
|---|---|---|---|
| Git-репозиторий, README, Wiki | 0–1 | `checks-git-docs.md` | `docs`, `git` |
| Командная работа: консистентность, арх. стиль | 0–1 | `checks-consistency.md` | `arch`, `style` |
| Качество исходного кода (Code Smells) | 0–1 | `checks-smells.md` | `smell`, `security` |
| Тест-кейсы (тест-план в 1-м спринте) | 0–2 | `checks-testing.md` | `docs`, `tests` |

Each file ends with **Known instances** — the concrete remarks the grader wrote on
2026-08-07, which is what the `regression: True` probes encode. Fixing only a named
file scores nothing next sprint: the grader cites examples, the probe hunts the class.

How to run the pass — the two lanes, scoring, grading target, report format, fix mode,
and waivers — is in **`stage-b.md`**. Read it before starting Stage B.

## Extending

New grading arrives → for each remark, name the **class** of defect it belongs to,
add that class to the matching `checks-*.md` table, and in the same commit either add
a generic rule to `probes/rules_*.py` (`regression: True`) or state that it is a
judgment item. Append the literal remark to that file's *Known instances*. Never
write a project file path into a rule — if a rule needs one, it belongs in
`config.json`.

Porting to another repository: edit `probes/config.json` only — layer roots, source
globs, doc/config/env paths, layer kind (`ui` | `service`), and each layer's
`forbidden_imports`. The catalogue itself is stack-agnostic.

A new criterion section → `checks-<slug>.md` plus a row above. Keep every file under
200 lines (`.claude/rules/coding-rules.md`).
