# Stage A — audit/fix loop rules

Target: a stable **>= 2.5 / 3.0** per layer. Run separately for `backend/` and
`frontend/`; each layer keeps its own `AUDIT_LOG.md` in its own directory.

## Zero-bias auditor

While running `auditor-prompt.md` you are an **independent strict auditor**:

- Judge only the current state of files and git history as read from the terminal.
- Ignore your own earlier edits and intentions. A half-finished fix scores as broken.
- Never round a score up because the direction is right.
- Dispatch each audit iteration as a **fresh subagent** (`Agent` tool,
  `general-purpose`), giving it only `auditor-prompt.md` + the layer directory. A
  fresh context cannot be sentimental about work it never did.

## Iteration algorithm

1. Run the auditor prompt (PHASE 1–3) as written.
2. Print the returned Score and exactly the returned finding list — no edits, no
   softening, no reordering.
3. Success gate:
   - Score >= 2.5 → run **one more** audit as confirmation. Confirmed → Stage A ends.
     Not confirmed → continue at step 4 with the lower score's findings.
   - Score < 2.5 → step 4.
4. Fix:
   a. Turn the findings into a task backlog, most severe first.
   b. Fix code, config, tests, documentation, or git hygiene.
   c. Commit atomically per logical block, Conventional Commits
      (`fix(ui): ...`, `refactor(api): ...`).
   d. Verify the layer still builds and its linters/tests pass
      (`ProductSpecification/technology.md` owns the commands).
   e. Back to step 1.
5. **Iteration cap: 7.** Minimum 5 when the first score is below 2.5. Hitting the cap
   without reaching 2.5 is not a failure to hide — write the remaining blockers to
   `AUDIT_LOG.md` and report them.

## Prohibitions

- Do not edit `auditor-prompt.md` or any scoring criterion.
- Do not add mock/dummy code to "pass" a check where real logic is required.
- Do not delete tests, weaken linter/type rules, or add blanket ignores to raise a score.
- Do not add a waiver (`probes/waivers.json`) to silence a Stage B failure during a
  loop iteration — waivers are a human decision, made outside a run.
- No infrastructure state changes; the fix goes into `infra/`
  (`.claude/rules/infrastructure.md`).

## AUDIT_LOG.md

After every iteration, append to `<layer>/AUDIT_LOG.md`:

```markdown
# Audit Log

## Iteration <N> — Score: <X.X> / 3.0 — <YYYY-MM-DD> — <commit sha>
### Fixed Issues:
- ...
### Outstanding Blockers:
- ...
```

Append only — never rewrite earlier iterations. The trend across iterations is the
evidence that the score is stable and not a lucky single run.
