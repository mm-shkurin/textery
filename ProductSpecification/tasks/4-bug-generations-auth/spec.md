# Task 4: Generations auth

Type: bug

## Problem

`POST /api/v1/generations` and `GET /api/v1/generations/{id}` accept anonymous callers. No
`Authorization` header is required, and no generation records who requested it.

**Observed** (frontend session probing the running instance, 2026-07-17; reproduced with `curl`):

- `POST /api/v1/generations` answers **201** to a request with no `Authorization` header at all.
- `POST /api/v1/generations` answers **201** to a request carrying the literal garbage token
  `Authorization: Bearer garbage`.
- `GET /api/v1/generations/{id}` returns any generation to any caller holding the id.

**Expected**, per the product rule stated by the product owner on 2026-07-17: *creating a document
— manual mode or AI generation — is only possible with a token.* There is no anonymous authoring
path in this product. An anonymous generation is not a lesser mode; it is a state that must not
exist. A generation belonging to another account must be indistinguishable from one that does not
exist.

**Frequency**: deterministic — every call, every time. Not a race, not load-dependent.

**Environment**: reproduced against the running instance on 2026-07-17. The endpoints are story-1
surface and have not changed since; `git log` shows no auth work on the generation slice.

**Impact**:

- Unmetered spend. Anyone with `curl` can drive GigaChat generation without registering. The
  frontend withholds the button, but the frontend is not a control — the probe bypassed it in one
  command.
- Cross-account read. `GET /api/v1/generations/{id}` is an IDOR. UUIDv4 ids are not enumerable,
  but an unguessable id is not authorization.

**Why this exists** (context, not root cause — see `root cause analysis`): the generation slice
was built in story 1, when no login existed and a request had no name to record. Story 7's
`/login` landed 2026-07-17. The documents slice hit the same problem and closed it — see
`ProductSpecification/stories/05-manual-mode/decisions/document-ownership-decision.md`, whose
`Consequences` section names the generation endpoints as still open.

## Reproduction

Against a running backend with the generation slice wired (story-1 surface — present on `main`):

1. Anonymous create — expect 401, observe **201**:

   ```bash
   curl -i -X POST http://localhost:8000/api/v1/generations \
     -H 'Content-Type: application/json' \
     -d '{"topic":"anything","volume_pages":1,"document_type":"doklad"}'
   ```

2. Garbage token — expect 401, observe **201**:

   ```bash
   curl -i -X POST http://localhost:8000/api/v1/generations \
     -H 'Content-Type: application/json' \
     -H 'Authorization: Bearer garbage' \
     -d '{"topic":"anything","volume_pages":1,"document_type":"doklad"}'
   ```

3. Cross-account read — create a generation as account A, note its `id`, then read it anonymously
   (or as account B). Expect 404, observe **200** with account A's content:

   ```bash
   curl -i http://localhost:8000/api/v1/generations/{id_from_step_1}
   ```

Port from `infra/.env` — do not assume 8000.
