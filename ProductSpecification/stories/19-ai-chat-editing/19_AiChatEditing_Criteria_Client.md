# AI chat editing — Acceptance Criteria (Client)

Client-side companion to `19_AiChatEditing_Criteria.md`; split out for the 200-line file
limit. Every bullet is a requirement a downstream frontend test must be able to go red on.

### Client

- Streamed chunks render as plain text for the whole stream; NO SSE event carries HTML.
  Sanitized HTML arrives only from the `GET /documents/{id}` re-fetch issued on the
  terminal event. A `<script>` chunk rendered mid-stream goes red, and so does a client
  that builds its final render by concatenating chunk text as markup.
- The three terminal events are handled distinctly: `done` re-fetches and unfreezes,
  `error` unfreezes with an error and a retry offer, `cancelled` unfreezes silently with
  no error banner and no retry. An unrecognized terminal kind is treated as `error`
  (unfreeze + retry), never as success.
- On `error`, cancel or client timeout the editor buffer reverts byte-identically to the
  pre-edit content and version — no partial model text left visible.
- Reconnect uses the `last_seq` from `GET /ai-edits/{edit_id}` as `Last-Event-ID`; a
  reconnect to an already-terminal edit terminates rather than hanging, because the server
  re-emits the terminal event unconditionally.
- The send control is disabled while a `POST /ai-edits` is in flight; one user gesture
  produces at most one effect. A retry after a network timeout reuses the same
  `Idempotency-Key` ONLY with an unchanged body — an edited instruction must carry a new
  key, or the server answers 422 and the user's new instruction is never silently lost.
- Overlapping reads for one document view are last-write-wins: a late response from a
  superseded request never overwrites the current render.
- Revisions panel and chat history each have distinct loading / empty / fetch-error states;
  a dropped SSE connection shows a visible reconnecting state, distinguishable from a
  stalled stream.
- Unsaved editor content is never silently discarded: sending an AI-edit instruction with a
  dirty buffer persists the draft first or blocks with a confirm; navigating away or
  refreshing with unsaved content fires a confirm-guard.
