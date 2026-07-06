# Technology Profile

## Methodology

This project follows the TDD/ATDD + Clean Architecture methodology described in:
- https://habr.com/ru/articles/1023094/
- https://habr.com/ru/articles/1023998/

Practically this means: strict red-green-refactor via `/continue`, ATDD chain
(red-acceptance → red-usecase → green-usecase → adapters → green-acceptance),
mandatory quality gates (test-review, coverage, refactor) before every commit,
and `progress.md` per story as the persistence mechanism across context resets.

tech-profile:
  backend: TODO # planned: python-fastapi-hex (custom profile, not yet authored)
  frontend: react-ts
  css: TODO
  browser-testing: TODO

## Backend

TODO — no built-in profile for FastAPI + Hexagonal Architecture yet.
Needs a new profile at `.claude/tech/python-fastapi-hex/` (coding.md, tdd.md,
infrastructure.md, templates/) plus a few stack decisions first: ORM
(SQLAlchemy? raw asyncpg?), migrations tool, DI approach, test runner/mocking
library. Fill this section and `.claude/tech/python-fastapi-hex/` together.

## Frontend

| Concern | Technology |
|---------|-----------|
| Language | TypeScript |
| Framework | React 18 |
| Build tool | Vite |
| Test runner | Vitest |
| HTTP mocking | MSW (Mock Service Worker) |

## CSS

TODO — decide with the user when frontend work starts (tailwind vs plain-css).

## Browser Testing

TODO — decide with the user when frontend work starts (playwright vs selenium vs cypress).

## Testing (Backend)

TODO — depends on backend profile decisions above.

## Infrastructure

| Concern | Technology |
|---------|-----------|
| Containerization | Docker / docker-compose |

## Conventions

### Backend

TODO — fill in once the python-fastapi-hex profile is authored.

### Frontend

| Concern | Convention |
|---------|-----------|
| Test skip marker | .skip |
| Dev command | npm run dev |
| Test command | npx vitest run |
| Node config syntax | process.env.VAR \|\| 'fallback' |

### Browser Testing

TODO
