# Decision: Bounded Unicode local-part with NFC-normalize-before-fold

**Date**: 2026-07-15 **Scenarios**: 2.4c

Email's ASCII-only regex rejects the NFC/NFD accented-email precondition scenario 2.4c needs, and a hazard-catalogue scan (groups 1/3/4/5/6/7) found that naively "accepting Unicode" reopens header/log-forging, homograph, and ReDoS surface the current regex closes.

| Rejected | Why |
|----------|-----|
| Permanent deferral (keep ASCII-only, skip scenario forever) | Spec explicitly requires it; scenario is testable and fixable without disproportionate cost once the character class is bounded. |
| Full RFC 6531 / email-validator library | New dependency + its own review surface, for a guarantee (full internationalized-email compliance) this story doesn't need — only case-fold/NFC uniqueness is in scope. |

**Chosen**: bounded Unicode local-part — accept Unicode `Letter`, `Mark`, `Decimal_Number` categories only (via `unicodedata.category()`), explicitly reject `Cc` (control), `Cf` (format, includes bidi-control/zero-width), `Zl`/`Zp`/`Zs` (line/paragraph/space separators). Pipeline order: length cap (`MAX_EMAIL_LENGTH`, unchanged) → `unicodedata.normalize("NFC", raw_value)` → character-class + structural validation → `.lower()` case-fold. Homograph pairs (e.g. Cyrillic `а` vs Latin `a`) are **intentionally distinct accounts** — uniqueness is by codepoint after NFC, not by visual appearance; not treated as a defect.

## Model

- `backend/domain/src/auth/email.py`: `_is_valid` gains a per-character category check for the local-part (replacing the ASCII character class in `_EMAIL_PATTERN`); domain label (after `@`) stays ASCII-only (no IDN/punycode support, out of scope). `__init__` normalizes (`NFC`) before the validity check and before `.lower()`.
- No new ports, no new domain entities.

## Edge Cases

| Case | Behavior |
|------|----------|
| Local-part with CR/LF/NUL or other `Cc` control chars | Rejected — `ValueError` / `INVALID_EMAIL`, same as any other malformed input. |
| Local-part with zero-width or bidi-control (`Cf`) codepoints | Rejected — same path. |
| Raw input far exceeding `MAX_EMAIL_LENGTH` | Rejected by the length check before `unicodedata.normalize` ever runs (order fixed above) — bounds the normalize cost. |
| Two concurrent registrations, same email in NFC vs NFD form | Both normalize to the identical stored string before the DB unique-constraint check; losing request gets `EMAIL_ALREADY_REGISTERED` (409), same mechanism as scenario 2.2/2.4a — no new concurrency primitive, the DB constraint is the sole serialization point regardless of which Unicode form arrived first. |
| Rolling deploy: old (ASCII-only) code reads a row written by new (Unicode/NFC) code | New-code rows containing non-ASCII local-parts are opaque strings to old code's read path (no re-validation on read) — old code only re-validates on writes, so it can read but not itself write a non-ASCII row until it's upgraded. No migration needed since the schema/column is unchanged. |
| Rejected/duplicate Unicode email in error response or logs | Existing error mapping (`{error_code, message}`, no raw field-value echo) already avoids echoing the submitted value — no new disclosure path introduced by widening the accepted character set. |
