# Stage B — running the manual checklist

Operational detail for the checklist pass. `SKILL.md` owns the pipeline and
scope; `grading-rules.md` owns the season's rules.

## Two lanes

- **Mechanical.** Items naming a probe ID are decided by the script — never by eye:
  `python .claude/skills/sprint-check/probes/run.py [--layer back|front] [--category docs|arch|smell|security|tests|git] --out <scratch>/probes.json`.
  The catalogue (`probes/rules_docs|arch|quality|git.py`) is stack-agnostic; every
  root, glob, and boundary comes from `probes/config.json`, which is the only file
  that knows this repo's layout. Rules expand per layer (`ARCH-SIZE@front`), skip
  layers that do not declare the input, and skip concerns that do not apply to the
  layer kind (`ui` vs `service`). The engine strips comments and docstrings while
  keeping string literals, ignores `node_modules/dist/coverage/…`, honours
  `probes/waivers.json`, and returns PASS/FAIL/WAIVED/UNKNOWN with `file:line`
  evidence. Git probes are pathspec-scoped to the layer.
- **Judgment.** Every other checklist item (SRP, God Object, cyclomatic complexity,
  re-render cascades, component responsibility, transport abstraction, commit
  granularity). Batch these per criterion and dispatch review agents in parallel —
  one agent per criterion per layer, each returning a verdict plus a quoted line.
  Never mark a judgment item PASS because a grep found nothing.

## Scoring

Owned by `grading-rules.md`: fixed per-criterion rule, one score per **repository**
(backend and frontend are separate GitVerse repos), then average and round by the
season's rounding rules. Never invent a free-hand estimate, never report the rounded
number without both repo scores.

## Grading target

**Default: the working tree.** Roughly 80 of the 90+ probes read file content, which
is identical before and after a push, so day-to-day runs need no worktree and no
network. Run them where the work happens.

**`--release`: one verification pass before pushing or before the Friday deadline.**
Three things the working tree cannot answer, and each has cost points before:

1. *What is actually committed.* Untracked material (test cases, docs) exists on disk
   and is invisible to a jury reading GitVerse. Only `git ls-files` on the release ref
   settles it.
2. *History.* Every `git`-category probe reads the history the jury sees. The split
   GitVerse repos may carry a squashed sync commit where the monorepo has an atomic
   series — the local history is not the graded one.
3. *Repository root.* In the split repo the layer directory **is** the root, so
   `backend/README.md` is graded as the project README, against the higher bar that
   implies (setup, containerization, architecture — all of it at the top level).

```
git fetch <artifact_remote> && git worktree add <scratch>/release-<layer> <release_ref>
python probes/run.py --layer <layer> --root <scratch>/release-<layer> --out <scratch>/probes.json
git worktree remove <scratch>/release-<layer>
```

Report the two runs separately: working-tree findings are the work queue, release-ref
findings are the score. A fix that exists locally but is not on the release ref counts
for nothing this sprint — list those under `## Not yet released`.

## Report

Write `_project_audit/sprint-check-<YYYY-MM-DD>-<back|front|full>.md` (overwrite the
same-day file of the same scope):

- Header: date, branch, HEAD, scope, Stage A final scores per layer.
- Per criterion: score per layer by the rule above, table
  `ID | layer | status | evidence (file:line)`.
- `## Regression watch` — every non-PASS `source:` item, first.
- `## New findings` — non-source FAILs, ranked by visibility to a grader reading the
  repo cold (README/root before deep internals).
- `## Delta` — versus the previous `sprint-check-*.md`: fixed / regressed / new counts,
  and every ID that changed status. Skip only when no earlier report exists.
- `## Needs a task` — findings requiring architecture work, one line of scope each.

In chat print only: Stage A scores, per-criterion score, and FAIL counts split
regression / new. Do not paste the tables.

## Fix Mode (`--fix`)

Only after the report exists. Fix in order, one commit per criterion,
`chore(sprint-check): ...`:

1. Regression items — the grader has already seen them.
2. New findings that are pure config/doc edits (README sections, `.env.example`,
   lint config, CSS variables, export style, endpoint map).

**Never auto-fix** anything changing runtime behavior or architecture (introducing a
state manager, splitting a God Object, moving nginx into Docker, replacing
`sessionStorage` with cookies). Those go to `## Needs a task` — the user decides; do
not file a task unasked (`.claude/rules/workflow.md`).

## Waivers

`probes/waivers.json` holds accepted violations: `{id, reason, expires, owner}`. An
expired waiver stops applying automatically, so an exception cannot quietly become
permanent. Adding one is a human decision — never during a Stage A iteration.

