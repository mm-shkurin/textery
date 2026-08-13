# Profile management — Notes & Considerations

## Warnings

### Functional Warnings

- **The rename runs through `save()`, which rewrites the aggregate.** Its update branch copies
  `email`, `password_hash` and `is_verified` from the loaded snapshot. SQLAlchemy's dirty check
  limits the emitted SET to changed attributes today, so this is not a full-row clobber — but
  that safety is an unasserted ORM implementation detail, and `increment_failed_attempts` /
  `transition_to_verified` write the same row out-of-band with direct UPDATEs that bypass the
  identity map. The spec therefore requires a name-only UPDATE rather than relying on it.
- **"No name" must have exactly one stored representation.** If `""` or `"   "` can reach the
  column, the email fallback (keyed on NULL) stops firing and the screen shows a blank identity
  instead of the address. A cleared account and a never-named account must be indistinguishable
  at rest.
- **An absent `name` key must not clear the name.** It reads as harmless while `name` is the only
  field, and becomes destructive the moment `PATCH /me` grows a second one — which story 8
  (subscription block) and story 14 (ТЗ §3 columns) both intend. Establishing the tri-state
  convention now is far cheaper than retrofitting it.
- **Last-write-wins is a decision, not an oversight.** Two tabs renaming concurrently: the second
  write wins and the first is silently lost. Because clearing is first-class, a stale tab can
  *undo* a rename rather than merely overwrite it. Proportionate for a display name; recorded so
  it is not mistaken for a missed hazard.

### UI/UX Warnings

- **The header's `null` identity stops being exceptional.** Today `ProfileMenu` treats a null
  email as an edge case; after the move to `/me` it is the state of *every* page for the duration
  of a request. A blank avatar that pops into initials is the default outcome if the loading state
  is not designed.
- **A failed header must not be silently identical to a healthy one.** The whole point of the
  degraded state is that it is visibly degraded — otherwise a `/me` outage looks like an account
  with no name.
- **«Выйти» must never depend on `/me`.** If the menu's contents are gated on a successful fetch,
  a `/me` outage traps the user in a session they cannot end.
- **«Мой профиль» is offered even when the header is degraded** — it links into a screen that will
  fail the same way. Either the item survives the degraded state deliberately, or it is hidden;
  either is fine, drifting into it is not.
- **An invisible name is worse than no name.** A name of zero-width characters renders as nothing
  in the identity row, blanks the avatar, and truncates the `aria-label` to «Меню профиля: » —
  destroying the one job that row has, which is answering "whose account am I in".

### Technical Warnings

- **The fakes cannot see a missed column.** `save()`'s own docstring records a production 500 born
  of this and says so outright: "The fakes append to a list, so no unit test could see it." Any
  guard on the write path that runs against a fake repository is not a guard.
- **Neither can a same-session re-read.** `create_session_factory` sets `expire_on_commit=False`
  and `find_by_id` is `session.get`, served from the identity map. A db test that writes and
  re-reads on one session passes on a row Postgres never received.
- **`asyncio.gather` of two PATCHes is not a concurrency test.** The coroutines serialize; the
  loser's SELECT lands after the winner's COMMIT and declines on its own. The project already
  wrote this down: "A test that reports green on the defect it names certifies the bug."
- **The OpenAPI `maxLength` will disagree with the domain bound.** OpenAPI counts UTF-16 units,
  the domain counts code points; they split at exactly the emoji boundary the tests assert.
  `project_query.py:6-9` carries the scar.
- **`word[0]` in `accountInitials` is safe by accident.** It slices UTF-16 code units and is only
  safe because email local parts are ASCII-ish in practice. A name is not, and an astral first
  character yields a lone surrogate rendered as U+FFFD.
- **A naive `created_at` will not raise.** `astimezone(UTC)` accepts it, reading it as host-local
  — correct in a UTC container, silently shifted on a developer machine.
- **`safeGet`/`safeSet` in `authSession` swallow failures by design.** A `/me` snapshot placed in
  that path inherits a second invisible failure mode on top of the network one.

---

## Suggestions & Future Enhancements

### Functional Suggestions

- A 409 with a version column, if the profile ever grows fields where a silent overwrite matters
  (it does not for a display name).
- Surfacing the deferred registration metadata (ТЗ §3) read-only on this screen once story 14
  collects it — the screen is the natural place to show a user what is stored about them.

### UI/UX Suggestions

- Show the name's remaining character budget rather than only refusing at the boundary.
- A success confirmation after save; today the only feedback is the header changing.

### Technical Suggestions

- The blankness predicate this story needs is **stricter** than the one `required_topic()`
  (`generation_validation.py`) already owns — it refuses `Cc`/`Cs` and strips invisible
  non-`Cf` characters — so it lands as a shared domain helper rather than a call into the
  existing one. Adopting it for topics too would close known-debt #8; that is story 1's call.
  Two implementations of "blank" will otherwise drift.
- The name value object is the fourth text VO with trim/NFC/bound; the shape is stable enough to
  factor.

---

## Technical Notes

### Load Considerations

The project's profile is **Throughput** (`ProductSpecification/ExpectedLoad.md`), and this story
converts a zero-cost local JWT decode into a network request on effectively every authenticated
page view — making `/me` the highest-rate endpoint in the product. The interview declined a load
scenario because the story adds no queue, no external API and no table scan; that is true and
does not address request rate, which is the profile's binding constraint. The load scenario is
therefore in scope (see `13_ProfileManagement_AcceptanceCriteria.md`).

The per-request cost itself is genuinely small: `find_by_id` is `session.get`, which consults the
request-scoped identity map, so `/me` does **not** issue a second PK select on top of the one
`get_current_owner_id` already performs. The risk is rate and connection-pool checkout, not
per-request work.

### Security Considerations

- **Stored XSS with the widest blast radius in the app** — the name is free-form user text echoed
  into a header rendered on every page. Length is the only input restriction by design, so the
  entire escaping burden sits at output, across two sinks (element text and the initials
  `aria-label`/`title` attribute).
- **Mass assignment** — the response is described as "the profile", which invites reusing the
  response DTO for the request. That model plus `save()`'s aggregate rewrite is a path to
  `is_verified` or `email` being set from a request body.
- **Account enumeration is not a risk here** — no route takes an account identifier, so there is
  nothing to enumerate; the guard is that it stays that way.
- **PII on a new surface** — email and name now flow through a new endpoint, a new response body,
  and a new client-side snapshot. `no-store`, log redaction, and snapshot clearing on sign-out are
  the three guards; the shared-machine case (sign out, no subsequent sign-in) is the one an
  account-switch test does not cover.

### Infrastructure Notes

The migration lands on a populated `accounts` table across a fleet that rolls one instance at a
time, so old code runs against the new schema during the overlap. `AccountModel` enumerates
columns explicitly rather than `SELECT *`, which should make the old code tolerant — nothing
asserts it today, which is why the N-1 guard is in scope. The downgrade drops the column and with
it every name entered since deploy.

### Integration Notes

No external service. The only new integration seam is internal: the frontend gains a hard
dependency on a backend route that did not exist, on every authenticated page. That is what makes
the degraded-render contract a requirement rather than polish — before this story a `/me` outage
was not a concept, and afterwards it degrades the entire authenticated shell at once.

---

## Additional Context

See `interview.md` for the round-by-round decision record: why `name` is nullable and starts
empty, why `/me` omits `is_verified`, why the header moves off JWT decoding, and the four pieces
of work other stories addressed to this one (OAuth unlink, account deletion, the per-account feed
preference, and the unclaimed ТЗ §3 registration metadata) with their deferral reasons.

The hazard-scan record — groups covered, verdicts, and every GAP's disposition — is in
`tests/00_Hazard_Scan_Record.md`.
