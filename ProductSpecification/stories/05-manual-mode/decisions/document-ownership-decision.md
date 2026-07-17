# Decision: `owner_id` column now, Bearer enforcement next sprint

**Date**: 2026-07-17 **Scenarios**: 2.1, 3.1, 4.1, 4.2, Security 2.1, 4.1

## The question

`documents_*.yaml` declares no security scheme, and `05_Security_Tests.md` states the story is
*"fully anonymous (no auth, no JWT)… a by-id document endpoint with no owner concept"*. The
story-5 frontend session flagged the consequence correctly: `GET /api/v1/documents/{uuid}` hands
any document to anyone holding the id, and `PUT` lets them overwrite it. **An unguessable UUID is
not authorization.** That is a textbook IDOR.

The anonymous posture was recorded when story #7 did not exist. Its `/login` landed and was
verified live on 2026-07-17, so the premise expired — the target is owned documents.

## The product rule that settles it

**Creating a document — manual mode or AI generation — is only possible with a token.** Stated by
the product owner on 2026-07-17. There is no anonymous authoring path in this product, so an
anonymous document is not a lesser mode; it is a state that must not exist.

That makes the spec's anonymous posture simply wrong rather than a defensible trade-off, and it
removes the question this ADR opened with.

| Rejected | Why |
|----------|-----|
| **Stay anonymous** (the current spec) | Contradicts the product rule outright. Also ships the IDOR the frontend session identified: an unguessable UUID is not authorization. |
| **Optional Bearer** — owner when a token is present, anonymous otherwise | Considered because the story-5 frontend does not send a token today (verified: `git grep -lniE "authorization\|bearer\|access_token"` over that branch's `frontend/src` returns **nothing**). Rejected: it manufactures exactly the anonymous document the product rule forbids, doubles every scenario across two access modes, and makes "client forgot the header" fail *silently* into an unowned row instead of loudly. |
| **`403` on a foreign document** | A 403 confirms the id **exists** — an existence oracle over the id space. Same reasoning as story 7's `INVALID_CREDENTIALS`, which deliberately collapses "no such account" and "wrong password". |
| **Nullable `owner_id`** | A permanent, untestable "unowned" state with no product meaning. |

## Chosen

- `Authorization: Bearer <access_token>` **required** on all three document endpoints.
- `documents.owner_id UUID **NOT NULL**`, FK → `accounts.id`, indexed.
- A document owned by another account is indistinguishable from one that does not exist — **404**.
- Missing, malformed, expired, or non-access token → **401**.

## Known consequence: the story-5 frontend must attach the token

It does not today — no file on `feature/05-manual-mode-frontend` reads a token, and
`documentApi.ts` sends only `Content-Type` and `Idempotency-Key` on all three calls. Until that
lands, every create/read/save answers **401** and the editor cannot function.

This is **not** a backend blocker and must not be worked around here: an anonymous fallback would
re-create the state the product rule forbids. The frontend work is small and unblocked — story 7's
frontend already performs the login that yields the token, so after the merge the value exists in
the app; it needs attaching to three `fetch` calls plus a guard that keeps an unauthenticated user
out of the editor route. Recorded here so the 401s are read as "the frontend half is pending", not
as a broken backend.

## What "next sprint" must do, so this is a bridge and not a leak

- Ownership must land as a **query predicate** (`WHERE id = :id AND owner_id = :owner`), never a
  post-read `if doc.owner_id != owner`. With the predicate the 404 falls out structurally and no
  code path *can* leak a foreign document; with the check, correctness rests on every future
  caller remembering the same `if`. `find_by_id` must be **replaced** by `find_by_id_and_owner`,
  not joined by it — leaving both keeps the unguarded one one autocomplete away.
- A foreign document must answer **404, not 403**. A 403 confirms the id exists, turning the
  endpoint into an existence oracle. Same reasoning as story 7's `INVALID_CREDENTIALS`, which
  deliberately collapses "no such account" and "wrong password".
- `read_access_subject` must mirror `read_refresh_subject`'s `type`-claim guard, or a 7-day
  refresh token becomes a document credential.
- The `Idempotency-Key` unique constraint must become `(owner_id, idempotency_key)` — see below.

## Idempotency-Key: the second gap the frontend raised

It asked three things the spec never answered. Decided here:

| Question | Answer |
|----------|--------|
| **TTL?** | None. The key is a column on the row it created, so it lives exactly as long as the document. A TTL would mean a replay silently creating a *second* document once the key aged out — the opposite of the guarantee. |
| **Scope — global or per-user?** | `UNIQUE (idempotency_key)` today (there is no user); **`UNIQUE (owner_id, idempotency_key)` when Bearer lands**. A permanently global namespace would let one account's key return another account's document — re-entering the IDOR through the idempotency door. The frontend spotted this coupling; it is real. |
| **Same key, different `document_type`?** | Return the existing document, 200. The key identifies the *logical create*, not the body: that is what makes it a retry token. Answering 409 would mean a client that retried with a corrected body gets a permanent error and no way to proceed. |

Race-safety: the **DB unique constraint**, not check-then-insert — mirroring story 7 scenario 2.2,
whose constraint-over-TOCTOU choice is exactly what made 2.4a's concurrent registration safe.
Flow: insert → `IntegrityError` → `ConflictException` → **`rollback()`** → re-read by key → 200.
The rollback before the re-read is load-bearing: after an `IntegrityError` the session is poisoned
and the next query raises `PendingRollbackError`. `RegisterUser` never hit this because it rolls
back and *aborts*; here we roll back and then *read*.

## Consequences, named

- **An IDOR ships for one sprint.** Anyone with a document UUID can read and overwrite it. Bounded
  by: UUIDv4 ids are not enumerable (Security 4.1), and the data is demo content. Not bounded by
  anything else. This is the cost of the deadline, accepted deliberately.
- `05_Security_Tests.md` section 7 (added with this ADR) describes the **target**, not this
  sprint's behaviour. Its scenarios stay unimplemented and are marked as such in
  `progress-backend.md` — not silently absent.
- `interview.md` and `05_ManualMode.md` are amended to point here rather than to claim either
  "anonymous forever" or "owned now".
