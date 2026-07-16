# Decision: Trimmed TDD cycle for the rest of sprint 1

**Date**: 2026-07-16 **Scenarios**: 3.2 onward (story 7), until end of sprint 1

Sprint 1's demo is **Friday 2026-07-17**, and the competition's deploy-or-zero rule scores
the entire sprint 0 if the published link is missing, doesn't open, or the app doesn't
function (`.memory-bank/sprint.txt`). Story 7's remaining backend scope is 27 scenarios,
measured at roughly 7–10 days on the pace of 13–15 July (158 commits, ~8 commits per
scenario, ~3 substantive scenarios per day). That does not fit, and no change to process
makes it fit — the gap is unwritten subsystems (login, JWT, refresh, lockout, hashing),
not ceremony overhead.

So the process is trimmed **and** the scope is cut. This records the process half; the
scope half is in `progress-backend.md`.

## What stays

The core loop, because it is what carries the correctness weight:

- **Test first, and it must actually go RED.** The predicted failure is still compared
  against the actual failure before green — an already-green test is still reported as
  already-green rather than dressed up as a RED phase.
- **Green implements only what the test demands**, then the code is left clean — no
  separate refactor pass, but no knowingly-dirty code committed either.
- Architecture rules (`.claude/rules/coding-rules.md`): strict inward dependency flow, no
  usecase calling a usecase, the 200-line-per-file hard cap.
- Honest commit messages recording the *why*, since commits are this project's only review
  surface and the AI audit reads them.

## What is dropped

| Dropped | Was |
|---------|-----|
| `/test-review` | A gating pass replacing loose assertions with exact equality |
| Separate `/refactor` commit | Behaviour commit + refactor commit per work unit; now one commit |
| `agent-review` + `premortem` passes | Two fresh-context reviews over every behaviour commit |
| ADR per `design` step | A decision record per non-trivial design choice |
| `(coverage: …)` follow-up steps | Targeted red/green steps closing measured coverage gaps |

One commit per scenario instead of two or three. Expected effect: ~8 commits per scenario
down to ~3, roughly 2.5–3x.

## The cost, named rather than discovered later

This is not a free simplification, and the evidence is from this story, this week:

- **`premortem` caught an entropy collapse that every other guard missed.** Scenario 3.1's
  green step was going to route `VerificationCode.generate()` through a new value object
  and delete `_CODE_MODULUS`. The natural typo — `secrets.randbelow(_CODE_DIGITS)` — draws
  0–5 instead of 0–999,999, formatting to `"000003"`: a `str`, six ASCII digits, matches,
  round-trips through `String(6)`. All four shape guards passed. Verification-code entropy
  would have dropped from 1,000,000 to 6 on the **live `/register`** path, with codes
  already mailed to real users. Verified by injecting the typo: only the new entropy guard
  failed.
- **`agent-review` caught a false claim in an ADR** (that `/verify` already mapped a
  malformed email to 400, when it actually 500s) and a **tautological assertion**
  (`generated.matches(generated.code)` is `self._code == self._code`, true by identity for
  any type — including the value object it claimed to guard).

Findings of that class will not be caught for the rest of this sprint. Accepted knowingly
under a hard external deadline, not because the passes were judged low-value.

Partial compensation: the guards those passes already produced are committed and stay live
(`TestVerificationCodeGenerateEntropy`, the both-axes ordering test, the trailing-newline
rejection). They protect the specific hazards already found; they do not find new ones.

## Scope

Applies from 2026-07-16 to the end of sprint 1, to story 7's backend scenarios only.
**The full cycle resumes in sprint 2** — this is a deadline exception, not a new default.
Security-critical work is explicitly **not** exempt: password hashing
(`05_Security_Tests.md` Scenario 1) still gets a real RED test proving an unhashed password
is not persisted, because that is the one defect this codebase already has in production
data and cannot fix retroactively.
