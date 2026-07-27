# Decision: `title` column and title-derived export filename

**Date**: 2026-07-27 **Scenarios**: 3.1 (with seams into 3.2 default filename, 3.3 header-injection, 3.6 grapheme truncation, Infra 3.1 rolling-deploy)

Why: the export filename must reflect the document `title`, but no `title` exists anywhere today — not on the `Document` entity, not in the save DTO, not in the schema. The field is a **cross-story additive column shared with story-5-extension** ("whoever lands it first adds it"); this session lands it. Two coupled decisions follow: how the column/field/save-path carry a title, and where the RFC 5987 filename derivation vs encoding live.

## Cross-story coordination

The `documents.title` column is shared with story-5-extension. This session adds the Alembic revision. It MUST be **additive and nullable** so a rolling deploy where old code still serves `Document` rows without selecting `title` keeps working (Infra 3.1 owns that scenario). If story-5-extension has already landed a `title` revision by the time green runs, adapters-discovery reuses it instead of adding a second — check `backend/adapters/db/migrations/versions/` for an existing `title` revision before authoring one.

## Model

| Layer | Change |
|-------|--------|
| Domain | `Document` gains `title: str \| None`. `create()` does NOT take title (mass-assignment guard, Security 2.1) — a new draft is born `title=None`; title is set only via save. `reconstitute()` accepts `title`. The entity stays anemic (no self-increment), consistent with the version-in-SQL-CAS precedent. |
| Schema | Additive **nullable** `title` column on `documents` (Alembic revision, `down_revision` = current head). No backfill, no NOT NULL — pre-migration rows read back `title=None` → default filename (Infra 3.1 / Sc 3.2). |
| Save | `SaveDocumentRequestDto` gains an **optional** `title: str \| None` (today Pydantic `extra="ignore"` silently DROPS it — the Sc 3.1 red-acceptance quirk). `SaveDocument.execute` gains `title`; the existing CAS `save_content_if_version_matches` extends to persist `title` in the SAME single SQL UPDATE (no read-compare-write — preserves the concurrent-write guarantee). |
| Export filename | `ExportDocument.execute` derives a plain filename from `document.title`: the title when present and non-empty, else the default stem `"document"`; the extension comes from `ExportFormat` (`.pdf`/`.docx`) — this also closes the Sc 2.2 hardcoded-`document.pdf` carry-forward. The derived filename goes on `RenderedExport.filename`. |
| Rest | The `/export` route RFC 5987-encodes `rendered.filename` into `Content-Disposition: attachment; filename*=UTF-8''<percent-encoded>` (replacing the hardcoded `filename=document.pdf`). |

## Where derivation vs encoding live

- **Derivation is policy** (default when absent, later CR/LF/quote stripping in Sc 3.3, grapheme truncation in Sc 3.6) → lives in the usecase/domain, on the path that already knows the format.
- **RFC 5987 percent-encoding is an HTTP wire concern** → lives in the rest adapter, next to the header it writes. `.pdf`/`.docx` and other RFC 5987 attr-chars (incl. `.`) pass through literally; the Cyrillic bytes + space are percent-encoded — matching the Sc 3.1 red literal `filename*=UTF-8''%D0%9F…%D0%B8%D1%80.pdf`.

## Rejected

| Rejected | Why |
|----------|-----|
| Title on `Document.create()` | Mass-assignment vector — a create-time field a client can set. The existing entity deliberately keeps `status/id/content/version` off `create`; `title` follows the same rule and is set via the owner-scoped save. |
| RFC 5987 encoding in the usecase | Encoding is HTTP presentation; putting it in the usecase leaks a wire format inward and makes `RenderedExport` carry a header-shaped string instead of a plain filename. |
| Full filename derivation (incl. encoding) in a domain value object | The percent-encoding depends on the transport (HTTP header), not on the document — a domain VO doing it would import an adapter concern. The default/truncation/stripping policy is domain; the encoding is not. |
| Separate `filename` CAS statement | A second UPDATE for title would reintroduce read-compare-write / a second round-trip; folding title into the existing version-CAS keeps one atomic statement. |

## Edge cases (owned where noted)

| Case | Behavior | Owner |
|------|----------|-------|
| Cyrillic title | `filename*=UTF-8''<rfc5987>.<ext>` | Sc 3.1 (here) |
| Title absent / empty / whitespace | default stem `document` → `document.<ext>` | Sc 3.2 |
| Title with CR/LF/quotes | stripped before encoding — cannot inject a header | Sc 3.3 |
| Long multibyte title | truncated on a grapheme boundary | Sc 3.6 |
| docx extension | `.docx`, not `.pdf` (extension follows format) | Sc 3.2 carry-forward + here |
| Pre-migration row (null title) after rolling deploy | old code serves the row; new code defaults the filename | Infra 3.1 |

No open fork — single viable approach per layer, each guard reusing an established pattern (nullable additive migration like `add_version_column`, optional DTO field, CAS extension, rest-layer header encoding). ADR recorded for the **cross-story migration coordination**, which is the one decision another session can collide with.
