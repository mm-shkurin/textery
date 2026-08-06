# Editor pages - API Endpoints

**No new endpoints.** Story 10 extends three existing contracts.

| Method | Path | Change |
|--------|------|--------|
| GET | /api/v1/documents/{document_id} | Response gains `page_settings` (nullable) |
| PUT | /api/v1/documents/{document_id} | Request gains `page_settings` (tri-state); response echoes it; 422 widened |
| GET | /api/v1/documents/{document_id}/export | No contract change — the render now applies the stored `page_settings` |

Specs: `api-specs/documents_get.yaml`, `documents_save.yaml`, `documents_export.yaml`.

## Notes

- **`page_settings` is tri-state on `PUT` and the three must stay distinguishable.**
  Omitted = stored value untouched; explicit `null` = reset to the default preset;
  a supplied object = **wholesale replace**, not a per-key merge. A content-only autosave
  must omit the field — sending a partial object would silently clear the user's header,
  footer and numbering flags back to defaults, and every other rule would still be satisfied.
- **No `page_settings` on `POST /documents`.** A freshly created document has no geometry
  to express; it is created with `NULL` and reads as the default preset. Adding it to
  create would duplicate the whole validation surface for a case the UI does not have —
  the page-setup panel only exists inside the editor.
- **No separate page-settings endpoint.** A `PATCH /documents/{id}/page-settings` would
  fork the optimistic-concurrency story: two writers on one row under two version tokens.
  Settings ride the existing `PUT` and its `version` CAS, so a content save and a settings
  save contend through one mechanism.
- **Unknown keys inside `page_settings` are rejected (422), while unknown top-level fields
  stay ignored** (story-5's server-owned-fields posture). Deliberate asymmetry: the object
  is re-serialized from a validated value object, so a silently dropped key would read back
  as a default the client never asked for.
- Page count is never in any payload — it is derived from content and geometry on read, and
  a stored count would go stale against the next edit.
