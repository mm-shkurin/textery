# Memory Bank — textery

## Overview

Full-stack project using continue-framework (Clean Architecture + strict TDD/ATDD) for
`backend/` and `frontend/`. `infra/` is a separate subtree run under its own harness
(`/plan → /build → /review → /debug`) — see `infra/.memory-bank/index.md` for that side.

Product: **Textery** — AI text-generation SaaS (see `ProductSpecification/BriefProductDescription.md`).
`stories.md` has an 8-story core build sequence (value-first: generation before auth)
plus a secondary backlog layered on top later.

This is also a graded competition project (Лаборатория, Сезон 2026) — see
`sprint.txt` for the scoring rules and [Sprint Plan](tasks/sprint-plan.md) for how that
maps onto the story backlog. **Hard rule: a broken/missing public deploy link on Friday
zeroes the entire sprint**, regardless of code quality — this dominates prioritization.

## Structure
- [Development Conventions](steerings/development-conventions.md)
- [Tech Details — Backend](tech-details/backend.md)
- [Known Debt](tasks/known-debt.md) — deliberately deferred decisions and their trigger conditions
- [Sprint Plan](tasks/sprint-plan.md) — 8-sprint roadmap + current sprint's task list
- Tech Details — Frontend (not started; frontend work hasn't begun)
- Product Overview (not started; pending `/interview` per-story)
