# ADR: Blank-title semantics and the title-clearing affordance

**Story:** 17 — Export document to PDF / DOCX
**Scenario:** 3.2 — A document with no title uses a default filename
**Date:** 2026-07-28
**Status:** Accepted (autonomous design decision — the story carries standing user approval to
proceed autonomously, recorded on Scenario 3.1, 2026-07-27)

## Context

Scenario 3.1 landed `documents.title`: a nullable column, set only through the owner-scoped save
(`PUT /api/v1/documents/{id}`), read by export to derive the filename. Its data-loss guard lives in
the db CAS writer — `title` is included in the UPDATE `.values()` only when it is not `None`, so a
content-only autosave that omits the title cannot `SET title = NULL`.

Scenario 3.2's red-acceptance found the branch one step over: `""` is not `None`, so it passes the
guard and executes `SET title = ''`, silently overwriting a stored title. Whitespace-only is worse —
`"   "` is truthy, so it survives derivation (`stem = document.title or "document"`) and reaches the
wire as `Content-Disposition: attachment; filename*=UTF-8''%20%20%20.pdf`, an effectively empty
filename the scenario forbids outright.

The red test pinned the decision that a blank title must not overwrite a stored one. Both review
passes over that commit (`ab97072`) then raised the same objection, independently and CREDIBLE:
combined with `title: str | None = None` being the only write surface, that decision leaves **no
wire value that can remove a stored title** — `None`, `""` and `"   "` would all mean "preserve". A
user who clears the title field would see it return on reopen and on every export filename.

## Decision

**The title field is three-state, and the three states are distinguished by what the client sent,
not by the value alone.**

| Wire shape | Meaning | Effect |
|---|---|---|
| key absent | no title intent (content-only autosave) | preserve the stored title |
| `"title": ""` or whitespace-only | no title intent | preserve the stored title |
| `"title": null` | explicit clear | `SET title = NULL` |
| `"title": "Отчёт"` | set | store verbatim |

Rationale for each edge:

**Blank preserves rather than clears.** A blank title is what a mount/hydration race, a
partially-initialised form, or a client that always serialises the field emits — it is the *default*
shape of "I have nothing to say about the title", not a deliberate erasure. Treating it as a wipe
makes silent data loss the failure mode of an ordinary frontend bug. Clearing is rare and
deliberate, so it gets the shape a client cannot send by accident.

**`null` clears, absent preserves.** Pydantic collapses both to `None`, so the route must
distinguish them with `model_fields_set` — the field being *present* is the signal. This is the only
place the two can be told apart, and it is exactly the RFC 7396 merge-patch convention: an absent
key leaves a value alone, an explicit `null` removes it.

**Titles are stored verbatim — no trimming.** The prescribed normalisation
`title.strip() or None` was rejected: it does two things, and the second is invisible. It maps blank
to "no intent" (wanted) *and* trims every legitimate title, so `" Отчёт "` silently becomes
`"Отчёт"`. Nothing in the suite can detect that — Scenario 3.1's `"Привет Мир"` has only an internal
space. Blankness is tested with `title.strip() == ""`; the stored value is never rewritten.

**Derivation strips independently of the save boundary.** `ExportDocument` derives
`stem = (document.title or "").strip() or "document"`. This is defense in depth, not belt-and-braces
duplication: the save-boundary rule only governs writes made *through it*. Rows written before this
green (today's `SET title = ''` is live), or by a migration, an import, an admin tool, or a future
create-with-title endpoint, bypass it entirely and would otherwise reproduce `%20%20%20.pdf`
forever. The filename is derived, so the derivation is where "never empty or null" is enforceable
for all inputs. Stripping here affects the filename only — the stored title is untouched.

## Consequences

- The `DocumentRepository.save_content_if_version_matches` port can no longer express intent with
  `title: str | None` — `None` is now ambiguous between "preserve" and "clear". It gains a
  three-state argument owned by the domain (a small `TitleUpdate` value object with `preserve()` /
  `clear()` / `of(value)`), so the rest adapter's Pydantic details never reach the usecase and the
  db CAS maps the three cases explicitly: omit from `.values()`, `SET title = NULL`, `SET title = ?`.
- The clear path is new behavior and therefore needs its own red/green, inserted into this
  scenario's step list rather than smuggled into a green whose tests do not cover it.
- Cross-story: `documents.title` is shared with story-5-extension, which owns the title-editing UI.
  The contract above is what that story's field must speak — an editor that serialises an emptied
  input as `""` will not clear the title; it must send `null`.
- Scenario 3.6 still owns the title *length* bound. Its filename obligation is now narrower and
  clearer: truncating the derived stem in `ExportDocument` bounds the `Content-Disposition` header
  regardless of what is stored, which is the same defense-in-depth argument made above.

## Alternatives rejected

**Blank clears the title.** Symmetrical and needs no `model_fields_set`, but it makes the common
accidental shape destructive — the exact incident Scenario 3.2's red test was written to forbid.

**Blank is a 422.** Loud instead of silent, which is better, but it fails the *whole* save: a
content-only autosave carrying a stray blank title would lose the user's content, trading a title
for a paragraph.

**Replace-only — titles can never be cleared.** Smallest change, and defensible if recorded. Rejected
because the capability loss is permanent and invisible: nothing in the API would signal it, and the
first person to notice is a user whose deleted title keeps coming back.
