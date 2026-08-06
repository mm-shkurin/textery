# Auto-generate: реферат — API Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with the prompt builder in the domain (1.x — pure, no infrastructure), then the
> provider handing off to it (2.x), then the end-to-end generation path (3.x).

---

## 1. Prompt Template — Domain

### 1.1 A реферат prompt asks for the реферат structure

```gherkin
Given a generation request for a реферат
When the prompt is built for it
Then the prompt asks for введение with актуальность and цель
And the prompt asks for разделы по теме
And the prompt asks for заключение with выводы
```

### 1.2 A реферат prompt forbids a bibliography

```gherkin
Given a generation request for a реферат
When the prompt is built for it
Then the prompt instructs that no список литературы is produced
```

A model asked for a реферат volunteers a bibliography unprompted, and its entries do not
exist. The instruction has to be present and negative — omitting the subject is not
enough. This scenario goes red if the ban is dropped while the structure survives.

### 1.3 A доклад prompt is unchanged by the move into the domain

```gherkin
Given a generation request for a доклад
When the prompt is built for it
Then the prompt is exactly the text the provider composed before this story
```

Story 1 is being finished elsewhere against the current доклад output. This scenario is
what makes the refactor mechanical rather than a silent behaviour change.

### 1.4 Every supported document type yields a prompt

```gherkin
Given each document type the domain supports
When the prompt is built for it
Then a non-empty prompt is produced for every one of them
```

Run per type, not over a collection in one assertion. A type without a template would
otherwise raise inside the worker — after enqueue, consuming the retry budget, landing
as `failed` with nothing the client can act on. This goes red when a fifth type is added
without a template, before any user meets it.

### 1.5 The topic cannot displace the template's instructions

```gherkin
Given a generation request for a реферат whose topic instructs the model to ignore
  previous instructions and write something else
When the prompt is built for it
Then the topic appears as delimited data
And the реферат structural instructions are still present
```

### 1.6 Requirements and extra wishes cannot displace the instructions either

```gherkin
Given a generation request for a реферат whose requirements and extra wishes both carry
  override text
When the prompt is built for it
Then both fields appear as delimited data
And the реферат structural instructions are still present
```

Covering `topic` alone is the canonical miss — it is the field the story talks about,
and the other two are equally user-controlled.

---

## 2. Provider Hand-off

### 2.1 The provider sends the prompt it was given

```gherkin
Given a built prompt for a реферат
When the generation is dispatched to the provider
Then the provider sends that exact text
And the provider composes no prompt text of its own
```

---

## 3. Generation Path

### 3.1 A реферат request is accepted

```gherkin
Given an authenticated user
When the user submits a generation request for a реферат
Then the request is accepted and reported as pending
```

### 3.2 A реферат generation completes end to end

```gherkin
Given an authenticated user
And the provider is stubbed to return a document
When the user submits a generation request for a реферат
And the generation completes
Then the user reads the generated content
And the generation records its type as реферат
```

### 3.3 An unsupported document type is still rejected

```gherkin
Given an authenticated user
When the user submits a generation request for a type the domain does not support
Then the request is rejected as an unsupported document type
```

### 3.4 A duplicate submission does not generate twice

```gherkin
Given an authenticated user who submitted a реферат request
When the same request is submitted again with the same idempotency key
Then the existing generation is returned
And the provider is called once
```

Story 1 established this for доклад. It is repeated here because the guard is keyed by
the request, and a реферат request is a request the guard has never seen.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `a generation request for a реферат` | `Generation` with `document_type="реферат"` |
| `the prompt is built for it` | Domain prompt builder invoked with the generation |
| `the text the provider composed before this story` | `"{document_type} на тему: {topic} ({volume_pages} стр.)"` |
| `each document type the domain supports` | Parametrized over `SUPPORTED_DOCUMENT_TYPES` |
| `appears as delimited data` | User text enclosed in the template's data delimiters, not concatenated into the instruction sentence |
| `an authenticated user` | Valid Bearer access token |
| `submits a generation request` | `POST /api/v1/generations` with `Idempotency-Key` |
| `the provider is stubbed` | GigaChat stub server, never the live API |
| `the user reads the generated content` | `GET /api/v1/generations/{id}` |
