# Auto-generate: реферат — Notes & Considerations

> **Provider and worker: read as GigaChat + `BackgroundTasks`, not OpenRouter + arq.**
> Written before 2026-07-09, when the engine was still planned as Claude via OpenRouter
> and the queue as `arq`. Neither shipped: generation goes through a direct `httpx`
> client to GigaChat (`backend/adapters/generation_provider/`), runs inline via
> FastAPI `BackgroundTasks`, and stale jobs are recovered by a periodic DB sweep —
> there is no worker process. `OPENROUTER_*` reads as the `GIGACHAT_*` credentials,
> "a stub OpenRouter server" as a stub GigaChat server. Behaviour is unchanged; the
> vendor and the transport are not. Source of truth: `ProductSpecification/technology.md`,
> `known-debt.md` #11 and #13. Verified against the code 2026-08-15.

## Warnings

### Functional Warnings

- **The two types can come out indistinguishable.** A реферат template that differs from
  доклад's one-liner only by adding three section names may still produce near-identical
  text. The acceptance criterion "the prompt names введение/разделы/заключение" is
  satisfiable by a prompt that changes nothing perceptible. Judge the output, not just
  the prompt, at least once by hand before calling the story done — even though no live
  model run is in the automated suite.
- **Список литературы is forbidden, not merely unrequested.** A model asked for a
  реферат will often append a bibliography unprompted. The instruction has to be
  explicit and negative; omitting the topic is not enough.
- **The доклад byte-identity criterion is load-bearing.** Story 1 is being finished in
  `textery-editor` and `textery-projects` against the current доклад output. If this
  refactor perturbs the доклад prompt even by whitespace, their tests may go red for a
  reason that has nothing to do with their work.

### UI/UX Warnings

- The type modal's disabled treatment ("скоро" badge) is this project's addition, not
  part of the Figma export — see story 1's spec. Removing it for реферат means editing
  that treatment's condition, not deleting a component.
- Every screen phrase for реферат already exists in `shared/documentTypes.ts` and has
  never been exercised, because the card was disabled. Wrong declension would surface for
  the first time here (`Тема реферата`, `Готовим ваш реферат`) — assert the strings
  rather than assuming the table is right.

### Technical Warnings

- Moving prompt construction out of `gigachat_provider.generate()` touches the one method
  the retry/timeout logic wraps. Keep the refactor mechanical; a behaviour change hidden
  inside it would surface as a retry-semantics bug, not as a prompt bug.
- A missing template entry would raise inside the worker — i.e. after the job is
  enqueued, consuming retries, ending as `failed` with no client-visible reason. That is
  why exhaustiveness is a test, not a runtime concern.

---

## Suggestions & Future Enhancements

- Structured templates for доклад (deferred to story 1's own worktree) and per-type
  volume ranges (реферат realistically wants 10–20 pages) are the obvious follow-ups.
  Both were considered and explicitly excluded — see `interview.md`.
- A титульный лист and автособираемое содержание need input fields and export-side layout
  the editor cannot render today; revisit after #17 (export) matures.

---

## Technical Notes

### Load Considerations

The реферат prompt is longer than story 1's one-liner, so input tokens per generation
rise. With `topic` ≤ 300 and the two optional fields ≤ 2000 each already capped, the
worst-case prompt remains bounded; the template contributes a fixed constant. Nothing
about the async design (`arq`, worker concurrency, job deadline) changes.

### Security Considerations

- **Prompt injection is the live one.** `topic` is user text concatenated into an
  instruction context — the LLM prompt is a sink in exactly the sense the hazard
  catalogue's output-encoding class means. Delimit user data and assert the structural
  instructions survive a hostile topic. This hazard exists in story 1 too; it becomes
  visible here because this story is the first to put *instructions* in the prompt worth
  overriding.
- The prompt embeds the user's topic and wishes; keep it out of info-level logs.
- No new secret, no new env var, no new endpoint, no authorization surface.

### Infrastructure Notes

None. No migration, no new service, no config.

### Integration Notes

- GigaChat integration is unchanged in shape — same endpoint, same auth, same retry
  policy. Only the message content differs.
- Note the drift between story 1's spec (which says OpenRouter throughout) and the
  running system (GigaChat, superseded 2026-07-09 — known-debt #11). This story is
  written against GigaChat, the thing that actually runs.

---

## Additional Context

See `interview.md` for the decisions this spec implements: domain placement of the
template, доклад left untouched, no bibliography, no per-type volume range, and the
"go independent of story 1" call.

### Hazard Catalogue Scan

Scanned against groups 1–8 (the full `_index.md` **Groups** list as of 2026-08-01).

| Group | Verdict |
|-------|---------|
| 1 Money, numbers & representation | Money/numeric edges: out of altitude — no arithmetic beyond story 1's pinned `volume_pages` budget. Text/encoding: **fired** → folded (Cyrillic template pinned byte-exact under NFC; `DocumentType` already normalizes) |
| 2 Re-run safety, ordering & atomicity | Idempotency, compute-then-commit, transaction boundary: dismissed — prompt building is pure, no side effect, no persistence. External-call failure: **fired** at the seam with group 5 → folded (a missing template must not raise inside the worker and burn the retry budget) |
| 3 Concurrency, consistency & distribution | Dismissed as a block for races/lost-update/read-after-write — nothing is read-modify-written. One residue folded: the builder must be stateless, since the backend runs multi-instance |
| 4 Data lifecycle & schema | Dismissed as a block — no schema change, no migration, no status-lifecycle change. (Story 3 fires this group; story 4 does not) |
| 5 Request boundary & input | Output-context encoding: **fired** → folded (prompt injection via `topic`). Default-branch/fail-open: **fired** → folded (exhaustive over `SUPPORTED_DOCUMENT_TYPES`, no catch-all). IDOR / mass assignment / absent-vs-null: dismissed — the request contract is untouched |
| 6 Scale & resource limits | Unbounded size: **fired** weakly → folded (prompt length bounded by existing field caps + fixed template overhead, asserted at max-length input). Amplification, exhaustion, retry storms, pagination: dismissed — unchanged from story 1 |
| 7 Time, operability & disclosure | Time/expiry and config drift: dismissed — no clock, no new env var. Secret/PII disclosure: **fired** weakly → folded (prompt carries user topic; not logged verbatim at info) |
| 8 Client / frontend | **Fired** → folded (client-as-untrusted: the card's `available` flag is UX only, the server allowlist is the authority, and эссе/сочинение stay API-reachable before their stories — stated deliberately). Action safety: dismissed — double-submit and idempotency are story 1's, unchanged |

Seams reconciled:

- **Exhaustiveness (group 5) × external-call failure (group 2).** Same hazard, two
  framings: a type with no template. One guard owns it — a parametrized domain test over
  `SUPPORTED_DOCUMENT_TYPES` asserting a non-empty prompt for each. It goes red the
  moment a fifth type is added without a template, before any worker ever sees it.
- **Prompt injection (group 5) × text handling (group 1).** One guard: a topic
  containing override text ("игнорируй инструкции выше…") is built into a prompt whose
  structural directives are still present and whose user text is delimited.

No unresolved GAPs.
