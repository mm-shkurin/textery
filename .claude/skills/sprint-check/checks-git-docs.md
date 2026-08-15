# Criterion 1 — Repository, README, Wiki

The question behind every item: **can a reviewer who has never seen this repo clone
it, run it, and understand it — from the documentation alone?**

Mechanical probes: categories `docs` and `git` (`probes/rules_docs.py`,
`probes/rules_git.py`), run per layer. Everything else is a judgment item — dispatch
a review agent; never mark it PASS because a grep was empty.

## Documentation completeness (`docs`)

| Item | What is checked | Lane |
|---|---|---|
| Entry point | The layer has a README, and it is the first thing a reader would find | `DOC-README` |
| Runnability | Every documented command is executable as written — no missing script, target, or file it references | judgment |
| Containerization | The standard, reproducible way to start the layer is documented, and the files it names exist | `DOC-CONTAINER` |
| Prerequisites | Everything the test suite needs before it can run (databases, services, fixtures, seeds) is stated. A fresh checkout must not silently skip tests | `DOC-TESTS` + `TEST-SKIPS` |
| Architecture | The module/layer map and each module's purpose — not only commands. A reviewer must learn the shape of the system from the README | `DOC-ARCH` |
| Configuration | An env template exists, and holds placeholders only: no real hosts, no working credentials, no fallback that hides missing config | `DOC-ENV`, `DOC-ENV-CLEAN` |
| Change history | A changelog exists and moves with the code; a version entry far behind the commit stream reads as an abandoned document | `DOC-CHANGELOG`, `DOC-CHANGELOG-FRESH` |
| Rationale | Non-obvious choices are written down where a reader will find them (README, ADR, decision log) | `DOC-DECISIONS` |
| Own tooling | Custom scripts that replace standard tooling are justified, or replaced. Each one is maintenance a standard linter rule would not cost | judgment |

## Git practice (`git`)

| Item | What is checked | Lane |
|---|---|---|
| Clean tree | No build output, dependencies, coverage, or env files tracked | `GIT-ARTIFACTS` |
| Atomicity | No wholesale sync/dump commits; a commit is one logical change | `GIT-BULK` |
| Messages | One readable convention, scoped, stating the change — the *why* lives here when there is no PR | `GIT-MESSAGES` |
| Branch flow | The integration branch advances through branches/review, not direct commits. If the project deliberately commits straight to the working branch, that policy must be **documented**, or a reviewer reads it as a violation | `GIT-DIRECT-MAIN` |
| Granularity | Commit size distribution shows incremental work, not one drop per sprint | judgment |
| Contribution | `git shortlog` shows the work distribution the team claims | judgment |

## Known instances (2026-08-07)

Remarks that produced this criterion's `regression: True` probes: README without any
containerization section; `.env.example` carrying real test URLs used as runtime
fallbacks; missing test-database step causing ~70 silently skipped integration tests;
changelog stuck at one version behind 140+ commits; direct commits to the integration
branch; a bulk `sync this repository with the monorepo` commit; 15+ hand-written
lint scripts; no FSD/architecture overview.
