# Story 12: Мои проекты (list/search/sort, grid + list view) — Progress

Shared story-level narrative, decisions, and Spec checklist. Per-layer scenario
checklists live in `progress-backend.md` and `progress-frontend.md` (created once
`test-spec` produces scenarios). `ProductSpecification/stories.md` is the cross-file rollup.

## Spec
- [x] interview
- [x] story — `12_MyProjects.md` + `12_MyProjects_Notes.md`; hazard scan over all 8 groups, every GAP folded or dismissed (record in the Notes file)
- [x] mockups — `mockups/desktop/{01-projects-grid,02-projects-list,03-search-empty}.html`, `mockups/mobile/01-projects-grid.html`
- [x] api-spec — `endpoints.md`; `api-specs/projects_list.yaml` + `api-specs/generations_repeat.yaml`; `documents_list.yaml`/`generations_list.yaml` marked deprecated. Folded the agent-review/premortem findings from the story commit
- [~] test-spec

## Decisions

- **New `GET /api/v1/projects` instead of extending the existing list endpoints.**
  Search + 4 sort orders + merging failed generations into one feed all break the
  keyset cursor, whose anchor must be immutable. `GET /api/v1/generations` and
  `GET /api/v1/documents` get marked deprecated and stay working. Reasoning in
  `interview.md`.
