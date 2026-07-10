## 2026-07-10 — task created and closed in one ad-hoc session

Origin: a competition-style automated code-quality audit prompt was run
against `backend/` only (not the full repo) and returned 2.5/3.0. The audit
findings drove this task directly — this task was created retroactively
after the fix was already implemented, not via `/task` before coding.

Two of five original audit findings were rejected on inspection rather than
implemented blindly:
- `GigaChatProvider` try/except — the audit assumed provider errors reached
  the REST unhandled-exception path uncaught, but `GenerateDocument.execute`
  already wraps `provider.generate()` in `except Exception`. Wrapping again
  in the provider would be dead code.
- Pydantic range constraint on `volume_pages` in the request DTO — would
  create two validation layers (422 from Pydantic vs. 400 from the domain's
  `ValidationException`) for the same rule, breaking the existing contract
  scenario 1.2 depends on.

Re-running the same audit prompt after the fix scored 3.0/3.0.

**Quirk for future work on this generation flow**: `GenerateDocument`'s
retry (`MAX_PROVIDER_ATTEMPTS = 2`) is a plain in-loop retry with no delay —
fine for the current synchronous BackgroundTasks execution, but if this ever
moves to a real queue (arq worker, deferred per known-debt #10/#11) the
retry should probably move to the queue's own retry/backoff instead of
living inside the usecase.
