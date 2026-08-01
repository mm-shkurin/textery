# Мои проекты — API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/projects | Merged owner-scoped feed: documents + unconverted generations. Search, 5 sort orders, offset paging. `api-specs/projects_list.yaml` (+ `projects_schemas.yaml` — one contract, split for the 200-line file limit) |
| POST | /api/v1/generations/{generation_id}/repeat | «Повторить» — re-run a failed/stalled generation with the same parameters. `api-specs/generations_repeat.yaml` |

Marked `deprecated: true` by this story, unchanged otherwise:
`GET /api/v1/documents`, `GET /api/v1/generations`. The `/{id}` singles are untouched.

## Notes

- **Two endpoints, not three.** No separate "recent projects" call — that section is the
  first `projects_recent_items` (4) items of the same page. A second request for a slice of
  data already in hand is the kind of endpoint the MVP rule exists to refuse.
- **Repeat is a sub-resource, not another `POST /generations`.** Re-posting to the create
  endpoint would have to carry an `Idempotency-Key`, and the browser's key is
  `crypto.randomUUID()` per call — so double-click, second tab, and retry-after-timeout each
  produce a second billed generation. Addressing the source generation by id gives the
  server the operation's identity for free, and the exactly-once rule becomes a database
  constraint on `repeat_of_generation_id` instead of a promise about client behaviour.
- **`preview` is a new field, `total` is a new concept.** The keyset endpoints deliberately
  omit `total` (counting per page is the scan a cursor avoids); offset paging needs it, and
  it therefore shares the search path's timeout and cancellation rather than being a second
  unbounded count.
