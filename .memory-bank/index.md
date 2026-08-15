# Memory Bank — textery

> **Замороженный материал, кроме `tasks/known-debt.md`.** Записан 07–08.07.2026 и с тех
> пор не сопровождается. Рекомендация зафиксирована аудитом 13.07 и не была отражена в
> самих файлах — исправлено 15.08.2026. Действующие источники истины:
>
> | Вопрос | Куда смотреть |
> |---|---|
> | Стек, команды, конвенции | `ProductSpecification/technology.md` |
> | Прогресс историй | `ProductSpecification/stories.md` + progress-файлы историй |
> | Что реально работает | `ProductSpecification/progress-summary.md` |
> | Отложенные решения | `tasks/known-debt.md` — **живой файл**, читать и обновлять |
> | Правила соревнования | `sprint.txt` — правила не менялись, актуально |
> | Инфраструктура | `infra/architecture.md`, `infra/.memory-bank/` |
>
> Устаревшее внутри этой папки, известное поимённо: `tasks/sprint-plan.md` (роадмап от
> 08.07, спринты с тех пор ушли вперёд) и строка «Tech Details — Frontend (not started)»
> ниже — фронтенд с тех пор вырос до шести фич-модулей.

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
- [Sprint Plan](tasks/sprint-plan.md) — 8-sprint roadmap, **зафиксирован 08.07 и устарел**
- Tech Details — Frontend — не заводился. Фронтенд давно есть (`frontend/src/features/`:
  landing, auth, generation, history, projects, profile), так что это не «работа не
  началась», а незакрытая страница memory-bank. Фактическое описание фронтенда живёт в
  `frontend/README.md`, `frontend/CONTRIBUTING.md` и `.claude/guidelines/frontend-rules.md`.
- Product Overview — не заводился; per-story `interview.md` играет эту роль
