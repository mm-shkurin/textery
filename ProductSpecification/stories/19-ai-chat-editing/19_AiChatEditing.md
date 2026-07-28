# AI chat editing of an existing document

## Brief Description

An open document gets edited by AI through a chat panel: the user writes an instruction
(optionally bound to a selection), the model rewrites the text, the result streams back
over SSE, lands as a new revision, and any revision can be restored.

## Flow

1. User opens a document in the story-5 editor (created manually or via story 18).
2. User types an instruction in the chat panel; optionally a text selection is attached.
3. Client `POST /documents/{id}/ai-edits` with `{message, selection?, base_version}` and a
   required `Idempotency-Key` → 202 `{edit_id, status: queued}`.
4. Backend persists a `DocumentEdit` + the user chat message, enqueues an arq job, returns.
5. Editor goes read-only ("AI is editing") with a visible cancel button and a client timeout.
6. Client opens `GET /documents/{id}/ai-edits/{edit_id}/stream` (fetch + ReadableStream,
   Bearer header) and renders events by increasing `seq`.
7. Worker calls the **document-edit provider** (a port separate from `GenerationProvider`),
   appending each chunk as an event row; the SSE endpoint tails those rows from the DB.
8. On completion the worker sanitizes the full result, applies it as a version-guarded
   save against `base_version`, writes a revision row and the assistant chat message, and
   emits a terminal `done` event carrying `{version, revision_number}`.
9. Client unfreezes the editor, loads the new content and version, appends the reply.
10. Revisions panel lists `GET /documents/{id}/revisions`; `POST /documents/{id}/revisions/{n}/restore`
    creates a *new* version whose content equals revision `n`.

## Acceptance Criteria

See `19_AiChatEditing_Criteria.md` — split out for the 200-line file limit.

## Validation Rules

| Field | Rule |
|-------|------|
| message | required, non-blank, max length in code points, pinned like `MAX_REQUIREMENTS_LENGTH`; stored as text, never rendered as HTML |
| selection | optional `{start, end}` in **code points**; `0 <= start < end <= len(content)`; null / empty / stale / out-of-range → 4xx |
| base_version | required; absent, `null` or `0` → 4xx; must equal current version, else 409 |
| Idempotency-Key | required on `POST /ai-edits`; same key → same `edit_id` |
| Last-Event-ID | optional integer; unknown/negative → from the start, never a crash |
| revision n | required positive integer, bounded; must belong to the caller's document in the path, else 404 |
| limit / cursor | server-capped; outside the allowlist → 4xx |

## Screen States

- **Editor + chat panel** — document left, chat right, message input enabled.
- **Editing (frozen)** — editor read-only, streaming text visible, cancel button, timeout.
- **Reconnecting** — SSE dropped mid-edit, distinct from a stalled stream.
- **Edit failed** — inline error from the `error` event, buffer reverted, retry offered.
- **Over quota** — chat input disabled with the reset hint.
- **Selection-bound prompt** — the attached excerpt shown above the input.
- **Revisions panel** — list (number, time, source: manual/AI/restore) + restore, with
  distinct loading / empty / fetch-error states.
- **Restore confirm** — restore creates a new version; nothing is destroyed.

## Core Requirements

- SSE, not WebSocket: no in-memory session state, no sticky routing. Backend is
  multi-instance — every piece of edit state lives in the DB.
- Edit events are persisted rows, not only pushed: the same table serves reconnect replay,
  the worker→web-instance channel, and the revisions timeline.
- Editing is a separate usecase per endpoint; no usecase calls another usecase. Shared
  logic (sanitize, apply-with-CAS, revision append) lives in the domain.
- The document-edit provider is its own port with its own fake (`fake` mode) so acceptance
  tests never call GigaChat.
- arq worker + Redis wiring is added in this story (compose, CI, config); story 1's
  `BackgroundTasks` path is not broken by it.
- New tables: `document_edits`, `document_edit_events`, `document_revisions`,
  `document_messages`.
- ACTION: measure GigaChat's real context window on the stand (`mmshkurin.ru`) before
  pinning the context-fit threshold.
