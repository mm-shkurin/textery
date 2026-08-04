# Decision: page_settings reads as a tri-state, and GET sheds title/generation_id

**Date**: 2026-08-03 **Scenarios**: 2.1 (constrains 2.2, 2.3, 2.4, 4.2)

A never-configured document must stay distinguishable from one configured to today's default
preset, and the frozen 2.1 acceptance test enforces that with an exact 8-key response body —
which the current `DocumentResponseDto` breaks by serializing `title: null` and
`generation_id: null`, two fields `documents_get.yaml` never declared.

| Rejected | Why |
|----------|-----|
| Keep `title`/`generation_id`, widen the frozen key set to 10 | Amends a committed red test and the api-spec to match code that drifted from it; an exact-but-larger key set is the weaker guard, and neither field has a reader on this endpoint |
| `dict \| None` end to end, no value object, no column | Leaves scenarios 3.1–3.8 with nowhere to put write validation but the DTO, and gives the `{}`-vs-NULL and migration guards no home |
| Materialize the defaults on read, add a `configured` flag | Freezes today's preset into every old document — the thing the story exists to prevent |
| `exclude_none` on the route to drop the two nulls | Would drop `page_settings: null` with them, inverting the very assertion 2.1 makes |

**Chosen**: a nullable `page_settings` carried unresolved from column to wire. SQL NULL → domain
`None` → JSON `null`; no default is constructed anywhere on the read path. `title` and
`generation_id` are removed from `DocumentResponseDto` so the served body matches
`documents_get.yaml` — verified to have no reader (frontend `documentApi.getDocument` destructures
neither; no acceptance statement asserts them).

## Model

- `Document.__init__` / `Document.reconstitute` — new `page_settings: PageSettings | None = None`.
- `Document.create` / `create_from_generation` — deliberately do NOT accept it. A never-configured
  document is `None` by construction, the same mass-assignment guard shape as `status`/`content`/
  `version`.
- `PageSettings` — frozen domain value object over the nine read-side keys. Its `from_stored`
  (missing key → default, undefined key → preserved and read as default) is written when 2.3/2.4
  demand it, not now.
- `documents.page_settings` — JSONB, NULLABLE, **no server default**, additive migration, no backfill.
- `DocumentResponseDto` — gains `page_settings: PageSettingsDto | None = None`; loses `title` and
  `generation_id`.
- `GetDocument` — unchanged.

## Edge Cases

| Case | Behavior |
|------|----------|
| Never configured | Column SQL NULL → `page_settings: null` on the wire, key present |
| Stored `{}` | An empty *configured* object — NOT conflated with NULL |
| Stored blob missing a defined key | Deferred to 2.3; until then the column only ever holds NULL or a server-written object |
| Stored blob carrying an undefined key | Deferred to 2.4; read must not reject or 500 |
| Row written before the migration | Reads back as `None`, never as a default |
| Repeated reads | Side-effect-free: no write-back, `version` and `updated_at` unchanged, column stays NULL |
| Migration re-applied | No-op; downgrade drops configured settings and is therefore forward-only |
