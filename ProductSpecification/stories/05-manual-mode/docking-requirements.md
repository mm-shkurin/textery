# Story 5 — backend docking requirements

**Audience: the backend session (`../textery`, `feature/05-manual-mode-backend`).**
Written 2026-07-17 from `feature/05-manual-mode-frontend`.

This is the frontend's side of the contract: what it will send, what it needs back, and
which decisions are settled versus still open. It **supersedes nothing** — `api-specs/documents_*.yaml`
remains the spec of record — but it names three places where those specs are now known to be
wrong or incomplete, and one decision (auth) taken by the product owner on 2026-07-17 that the
specs do not yet reflect.

> **Status: the frontend does NOT work against these contracts today.** Five blockers, all
> verified by execution, are listed at the bottom. Do not read "the frontend is done" from
> `progress-frontend.md`'s checkboxes — no call in this story has ever reached a real server.

---

## 1. Authentication — DECIDED 2026-07-17, not yet in the specs

**"Пользователь ничего не может сгенерировать и написать, если он не авторизован."**

The `documents_*.yaml` specs declare **no security scheme at all** and `DocumentResponse` has
**no owner field**. That is now known to be wrong, not deliberate sequencing.

Required on **all three** endpoints:

| | |
|---|---|
| Header | `Authorization: Bearer <access_token>` — required |
| Missing/invalid/expired | `401` |
| Ownership | Every document belongs to the authenticated user |
| Another user's `document_id` | **`404`, not `403`** — a 403 confirms the document exists and leaks ids |
| `Idempotency-Key` scope | **Per-user.** A global scope would let one user's key replay return another user's document |

Without ownership, `GET /api/v1/documents/{uuid}` serves any document to anyone holding the id.
UUID unguessability is not authorization.

**Open for the backend/spec owner:** whether `DocumentResponse` should expose the owner id at
all. The frontend does not need it — it only ever reads its own documents. Omitting it is fine
and leaks less.

## 2. `document_type` — the wire value must be Latin

The specs say `enum: [доклад, эссе, сочинение, реферат]` (Cyrillic). The client's `DocumentType`
is `'doklad' | 'essay' | 'sochinenie' | 'referat'` (Latin, `documentTypes.ts:1`). Today the client
sends Latin, so **every create 422s on "Unsupported document_type"** — independently of blocker 3
below, meaning fixing either one alone still creates nothing.

**Frontend's requirement: accept Latin.** Reasoning, so it can be overruled on better grounds:

- `DOCUMENT_TYPES[].id` already doubles as client-side identity — mode-modal state, React keys.
  Changing the union is not a rename; it touches component state.
- Cyrillic in a JSON enum invites encoding bugs across proxies, logs, and URLs for no benefit.
- The Cyrillic strings are **display labels**, a UI concern. The wire wants a stable identifier.

If the backend prefers Cyrillic on the wire, say so and the frontend maps Latin→Cyrillic at the
API boundary instead — that is a small, contained change. What must **not** happen is the two
sides disagreeing silently, which is the current state. **This needs an explicit answer before
the frontend's green phase.**

## 3. The three endpoints

### `POST /api/v1/documents`

```
Authorization: Bearer <token>        required
Idempotency-Key: <string, 1..128>    required, per-user scope
Content-Type: application/json

{ "document_type": "doklad" }        <- the ONLY field
```

- **`201`** — created, empty, no `Generation` ever created.
- **`200`** — this key was seen before: return the existing document, do not create a second.
- **`401`** — no/invalid token.
- **`422`** — unsupported `document_type`, or the body carries a server-owned field
  (`status`, `id`, `content`).
- **`500`**.

Both `200` and `201` return `DocumentResponse` (below). **`version` must be present on the
create response** — the frontend has no other legitimate source for it, and guessing it is
blocker 4.

**Still unspecified, and the frontend cannot answer it:**
- The key's **TTL**. How long must a replay return the original?
- Same key, **different `document_type`** — return the original, or `409`/`422`?

### `GET /api/v1/documents/{document_id}`

```
Authorization: Bearer <token>        required
```

`200` (`DocumentResponse`) / `401` / `404` (absent **or** not yours) / `500`.

### `PUT /api/v1/documents/{document_id}`

```
Authorization: Bearer <token>        required
Content-Type: application/json

{ "content": "<full HTML>", "version": 7 }
```

- **`200`** — saved. Idempotent for identical `(content, version)`. The response body **must
  reflect the sanitized, persisted content**, not the submitted bytes.
- **`400`** — `content` over 200 000 chars. Rejected whole, never truncated.
- **`401`** / **`404`** (absent or not yours).
- **`409`** — stale `version`; another save landed first.
- **`422`** — body carries a server-owned field (`document_type`, `id`, `status`).
- **`500`**.

`version` increments on every successful save.

### `DocumentResponse`

```
document_id  uuid
document_type
status        enum: [draft]
content       sanitized HTML; post-sanitization, NOT necessarily byte-identical to what was sent
version       int — optimistic-concurrency token, required on the next PUT
created_at    / updated_at
```

## 4. What the frontend sends as `content` — read this before writing the sanitizer

`ManualEditor.tsx:56` sends `editor.getHTML()`. The editor's schema is deliberately narrow:
`Document.extend({ content: 'inline*' })` — **no paragraph or heading nodes at all**. Every
block-looking feature is implemented as an inline **Mark**, so the markup is flat:

- `<strong>`, `<em>`, `<s>`, `<u>`, `<code>` — ordinary inline marks
- `<blockquote>`, `<h3>` — **marks, not blocks**, wrapping a line inline
- `<pre><code>…</code></pre>` — a mark rendering a nested pair
- `<div style="text-align: center">` — a mark; the alignment is an inline `style`, since no tag means "centered"
- `<hr>` — a custom **inline atom node**
- `<a href target rel>` — `target="_blank"`, `rel="noopener"`

**The sanitizer must not assume well-formed block structure**, and must not strip `<div style>`,
`<h3>`, or `<blockquote>` merely because they appear inline — that is this editor's normal output.
If the sanitizer rewrites any of it, the frontend currently **cannot tell** (see blocker note on
`saveDocument` discarding the response's `content`), and the editor will keep displaying markup
the server does not have.

**Requirement: tell the frontend what the sanitizer strips**, ideally by just returning the
sanitized `content` in the `PUT` 200 as the spec already says. The frontend owes the other half —
adopting it.

## 5. The frontend's five blockers — all measured, none fixed

Ordered by what bites first on docking.

1. **No authentication anywhere.** `grep -rn "Authorization\|Bearer\|access_token" frontend/src`
   → zero hits outside tests. No token storage, no auth files. `generationApi.ts` (story #1) is
   the same. Auth lives on an unmerged branch (`feature/07-authorization-frontend`). Given the
   2026-07-17 decision, **every call in this story currently fails at the door.**
2. **`POST` sends `content: ''`** (`documentApi.ts:22-25`) — a server-owned field → `422`.
   No document is ever created.
3. **`document_type` is Latin against a Cyrillic enum** → the *other* `422`. Independent of (2).
4. **`version` is dropped on create** (`documentApi.ts:19` parses `as { document_id, status }`);
   `useDocumentInit.ts:38-40` never calls `setVersion`, so `ManualEditor.tsx:38`'s `useState(1)`
   guess ships on the first PUT → `409`, blaming a concurrent save that never happened.
5. **`Idempotency-Key` is minted per-call** inside `createDocument` → the spec's `200` replay
   branch is unreachable by construction. With `main.tsx:7`'s `StrictMode` double-invoking
   effects (the `cancelled` guard suppresses `setState`, not the fetch), that is **two documents
   per dev mount** — measured: `fetch count = 2, distinct keys = 2`.

(2), (4) and (5) have a red phase committed (`c586f16`); it is knowingly incomplete — see
`progress-frontend.md`'s "Backend-docking contract gaps" section, which records why the obvious
green would ship all three defects with a fully green suite.

## 6. Why this was invisible until 2026-07-17

Every scenario's `red-frontend-api`/`green-frontend-api` step was marked `[S]` with the reason
*"no API call: formatting is client-side editor state only"*. True of toggling marks. **False of
the payload** — `getHTML()` goes over the wire. Scenario 7.9's premortem flagged that exact
misclassification and it was recorded, not acted on. Every `red-selenium`/`green-selenium`/`demo`
step is also `[S]` (backend on a parallel branch), so **no test in this repo has exercised these
calls against anything but a `vi.fn()` the test itself wrote.** The specs were the only contract,
and nobody had read them against the client until now.
