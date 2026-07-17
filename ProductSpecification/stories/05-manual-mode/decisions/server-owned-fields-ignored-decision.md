# Decision: Server-owned fields in a request body are ignored, not rejected

**Date**: 2026-07-17 **Scenarios**: 1.2, 5.4, Security 2.1

The spec contradicts itself on what happens when a client sends `status`, `id`, or `content` on
`POST /documents` (or `document_type`/`id`/`status` on `PUT`). Both readings are defensible; they
cannot both ship.

| Source | Says |
|--------|------|
| `api-specs/documents_create.yaml` — 422 | *"Unsupported document_type, **or a request body containing a server-owned field** (status, id, content)"* → **reject** |
| `api-specs/documents_save.yaml` — 422 | *"Request body contains a server-owned field (document_type, id, status)"* → **reject** |
| `tests/01_API_Tests.md` 1.2 — *"**Ignore** server-owned fields in the request body"* | *"the created document's status is `draft`, **not the attacker-supplied value**"* → document **is created**, fields dropped |
| `tests/01_API_Tests.md` 5.4 — *"**Ignore** server-owned fields in the save request body"* | *"only the content and version fields are ever applied"* → **ignore** |
| `tests/05_Security_Tests.md` 2.1 | *"only the server-controlled defaults are **ever persisted** for those fields"* → **ignore** |

| Rejected | Why |
|----------|-----|
| Reject with 422 (the two yamls) | Loud, and the frontend already believes it. But it is outvoted 3:1 by the test specs — including two whose **titles** are the word "Ignore" — and it contradicts story 7's scenario 1.5, named identically ("Ignore server-owned fields in the request body") and shipped as an ignore. Adopting it would mean two mass-assignment taxonomies on one API, decided by which story a route belongs to. |
| Both (reject on create, ignore on save) | Splits the rule by verb for no reason a client could predict. |

**Chosen**: **ignore**. Fix the two yamls; keep the test specs.

## Model

The rule is enforced by **absence, not by filtering**. `Document.create(...)` does not take
`status`, `id`, or `content` as parameters, and `CreateDocumentRequestDto` declares only
`document_type`. Pydantic's default `extra="ignore"` drops unknown keys before the router ever
sees them. So the decision is really: **do not add `extra="forbid"`**, and do not add a
denylist of field names.

That ordering matters. A filter (`body.pop("status", None)`) is a list someone must keep in sync
with the entity; a constructor signature that has no such parameter cannot be passed one. Security
2.1's requirement — "only the server-controlled defaults are *ever persisted*" — is then a property
of the type, not of a guard.

## Edge Cases

| Case | Behavior |
|------|----------|
| `POST {"document_type": "эссе", "status": "completed", "id": "<uuid>", "content": "x"}` | 201; `status="draft"`, server-generated `id`, `content=""`. The three extra keys never reach the domain. |
| `PUT {"content": "…", "version": 3, "document_type": "реферат", "id": "<uuid>", "status": "completed"}` | 200; only `content`/`version` applied; type, id, status unchanged. |
| `POST` with an unsupported `document_type` | Still **422**. This decision removes only the *server-owned-field* clause from the 422; the enum check is untouched. |
| `Idempotency-Key` outside 1–128 | Still rejected. It is a **header**, not a body field — this decision does not reach it. |
| Client sends a typo'd field (`documnet_type`) | Silently ignored, then 422 for the *missing* required `document_type`. Accepted: the required-field error still fires, so the request does not succeed quietly. |

## Consequences

- **The story-5 frontend's `content: ''` on `POST` stops being a defect.** It was logged as one
  (its own A/B/NEW-1) on the assumption the yaml was authoritative. Under this decision the field
  is simply dropped. Worth telling that session explicitly — a "fixed" defect that was never a
  defect will otherwise be re-fixed.
- Silent dropping means a client mis-binding a field gets no signal. Accepted: it is what
  `/register` already does, and the alternative is a bespoke 422 taxonomy per story.
