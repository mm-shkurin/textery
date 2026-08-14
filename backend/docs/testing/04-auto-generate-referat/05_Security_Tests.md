<!-- COPIED FILE. Source of truth: ProductSpecification/stories/04-auto-generate-referat/tests/05_Security_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: реферат — Security Tests

> **Implementation Order**: 1.x is the story's live attack surface — the prompt is the
> first one in this product to carry instructions worth overriding. 2.x-3.x guard
> disclosure and the boundary between UI availability and authorization.

---

## 1. Prompt Injection

### 1.1 A hostile topic does not take over the generation

```gherkin
Given an authenticated user
When the user submits a реферат whose topic instructs the model to disregard its
  instructions and produce unrelated output
Then the prompt sent to the provider still carries the реферат structural instructions
And the hostile text is carried as delimited data, not as an instruction
```

The LLM prompt is a sink in the same sense as HTML or SQL: user bytes are concatenated
into a context that interprets some of them as structure. Story 1 had no instructions in
the prompt to override, so the hazard was latent; this story is where it becomes real.

### 1.2 Every user-controlled field is treated as data

```gherkin
Given an authenticated user
When the user submits a реферат whose requirements and extra wishes carry override text
Then the prompt still carries the реферат structural instructions
And both fields are carried as delimited data
```

---

## 2. Disclosure

### 2.1 The prompt is not written to the log verbatim

```gherkin
Given a реферат request whose topic contains a distinctive sentinel value
When the generation is dispatched
Then the sentinel does not appear in captured log output at info level
```

The prompt now embeds topic, requirements and extra wishes — the user's own words about
their work. Story 1 redacted the provider credential; this covers the payload.

### 2.2 A provider failure does not leak its raw body

```gherkin
Given the provider is stubbed to fail with a body containing a sentinel value
When a реферат generation is dispatched and fails
Then the failure reported to the client contains no sentinel
And the client sees only the sanctioned failure contract
```

Inherited from story 1's requirement, re-asserted on the реферат path because the path is
new even though the handler is not.

---

## 3. Client Trust Boundary

### 3.1 A disabled card does not close the API

```gherkin
Given an authenticated user
When a generation request for эссе is submitted directly to the API
Then the request is accepted
```

Deliberately asserts acceptance, not rejection. The server's allowlist has carried all
four types since story 1 and the card's `available` flag is UX. Writing this down as a
passing scenario prevents a future reader from "fixing" the gap with a server-side gate
that stories #2 and #3 would then have to remove — and prevents anyone assuming a
disabled card is an authorization boundary.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `an authenticated user` | Valid Bearer access token |
| `submits a реферат` | `POST /api/v1/generations` with `document_type="реферат"` |
| `the prompt sent to the provider` | Text captured at the GigaChat stub |
| `delimited data` | Enclosed in the template's data delimiters, not spliced into the instruction sentence |
| `a distinctive sentinel value` | A fixed improbable string asserted absent, not a substring check on the raw input |
| `captured log output` | Log handler captured in-test |
| `the sanctioned failure contract` | `ErrorResponse` — `error_code` + generic message, no upstream body |
