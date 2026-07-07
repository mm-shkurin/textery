# Auto-generate: доклад — API Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with request validation (no infrastructure needed), then the happy-path create,
> then the mandatory re-run-safety guards, then read operations (which depend on a
> generation existing), then failure-handling, then listing.

No prerequisite-resource guards apply to this story (unlike board/column-style
dependencies elsewhere) — `POST /generations` has no parent resource that must exist
first; the only "guard" this story has is field-level validation, covered in section 1.

---

## 1. Create Generation — Validation

### 1.1 Reject request with missing topic

```gherkin
Given a generation request without a topic
When the client submits the request
Then the response is a validation error
And no generation is created
```

### 1.2 Reject request with out-of-range volume

```gherkin
Given a generation request with volume_pages of 0
When the client submits the request
Then the response is a validation error
And no generation is created

Given a generation request with volume_pages of 11
When the client submits the request
Then the response is a validation error
And no generation is created
```

### 1.3 Reject requirements/extra_wishes exceeding the length limit

```gherkin
Given a generation request whose requirements text exceeds the maximum length
When the client submits the request
Then the response is a validation error
And no generation is created
```

### 1.4 Reject unsupported document type

```gherkin
Given a generation request with a document type other than "доклад"
When the client submits the request
Then the response is rejected as unprocessable
And the document type is never silently substituted with "доклад"
```

### 1.5 Ignore server-owned fields in the request body

```gherkin
Given a generation request whose body also sets a status and an id
When the client submits the request
Then the created generation's status is "pending", not the attacker-supplied value
And the created generation's id is server-generated, not the attacker-supplied value
```

### 1.6 Ignore a client-supplied creation timestamp

```gherkin
Given a generation request whose body also sets a created_at timestamp
When the client submits the request
Then the created generation's created_at reflects server time, not the attacker-supplied value
```

### 1.7 Accept and reject requirements/extra_wishes length limits for Cyrillic text

```gherkin
Given a generation request whose requirements text is exactly 2000 Cyrillic characters
When the client submits the request
Then the request is accepted

Given a generation request whose requirements text is 2001 Cyrillic characters
When the client submits the request
Then the response is a validation error
```

---

## 2. Create Generation — Happy Path

### 2.1 Valid request is accepted and queued without waiting on the LLM call

```gherkin
Given a valid generation request for "доклад"
When the client submits the request
Then the response confirms the generation was created
And the generation's status is "pending"
And the response is returned without waiting for the document to be generated
```

### 2.2 An entirely Cyrillic request round-trips without corruption

```gherkin
Given a generation request with an entirely Cyrillic topic and requirements
When the request is processed end-to-end
Then the stored and returned text matches exactly, with no encoding corruption
```

---

## 3. Create Generation — Re-run Safety (idempotency)

### 3.1 Replaying the same idempotency key does not create a duplicate generation

```gherkin
Given a valid generation request submitted with idempotency key "key-1"
And the request has already been accepted once
When the client submits the identical request again with idempotency key "key-1"
Then the response refers to the original generation, not a new one
And exactly one generation exists for that idempotency key
```

### 3.2 A redelivered background job does not reprocess an already-progressing generation

```gherkin
Given a generation whose background job has already been claimed by a worker
When the same job is redelivered to another worker before the first one finishes
Then only one worker's processing is accepted
And the generation is not processed twice
And at most one document is produced for that generation
```

---

## 4. Get Generation Status

### 4.1 A pending generation reports its status without document content

```gherkin
Given a generation that has just been created by submitting a real creation request
When the client immediately requests its status afterward
Then the response reliably reports status "pending" — never a not-found response
And no document content is included
```

### 4.2 A completed generation includes the document content

```gherkin
Given a generation that has finished successfully
When the client requests its status
Then the response reports status "completed"
And the response includes the generated document's content
```

### 4.3 Requesting a non-existent generation reports not found

```gherkin
Given no generation exists with a given id
When the client requests that id's status
Then the response reports the generation was not found
```

---

## 5. Generation Lifecycle — Failure Handling

### 5.1 A permanent generation-provider error fails fast without exhausting retries

```gherkin
Given a generation whose document-generation call is rejected as permanently invalid
When the background job processes it
Then the generation moves directly to "failed"
And no further attempts are made for that generation
```

### 5.2 A transient generation-provider error is retried and can still succeed

```gherkin
Given a generation whose document-generation call fails once with a transient error
When the background job retries it
Then the retried attempt succeeds
And the generation reaches "completed"
```

### 5.3 Exhausting the retry budget fails the generation, never leaves it stuck

```gherkin
Given a generation whose document-generation call keeps failing transiently
When the background job exhausts its bounded retry budget
Then the generation moves to "failed"
And the generation never remains in "pending" or "in_progress" indefinitely
```

### 5.4 A generation abandoned by a dead worker is eventually reconciled

```gherkin
Given a generation whose worker died mid-processing without completing or failing it
When enough time has passed with no further progress
Then the generation is reconciled to "failed"
And this happens even though no explicit retry-exhaustion error ever occurred
```

### 5.5 A generation still within its normal processing window is not prematurely reconciled

```gherkin
Given a generation that is still legitimately being processed, well within the
  reconciliation staleness window
When the reconciliation check runs
Then the generation is left untouched
And it is not incorrectly moved to "failed"
```

### 5.6 A worker's genuine completion is never clobbered by a concurrent reconciliation sweep

```gherkin
Given a generation whose worker is completing it at the same moment the reconciliation
  sweep considers it stale
When both the completion and the sweep act on the generation at nearly the same time
Then exactly one outcome wins atomically
And a real "completed" result is never overwritten back to "failed" by the sweep
```

---

## 6. List Generations

### 6.1 Listing returns generations across all callers, most recent page first

```gherkin
Given generations exist from multiple different callers
When a client requests the generation list
Then the response includes generations regardless of who created them
And the response includes a cursor for the next page
```

### 6.2 Paginating with a cursor is stable while new generations are being created

```gherkin
Given a first page of generations has already been read via its cursor
And a new generation is created after that read
When the client requests the next page using the returned cursor
Then the second page does not repeat any generation from the first page
And the second page does not skip any generation that existed at the time of the first read
```

### 6.3 The list caps its page size even when far more generations exist

```gherkin
Given far more generations exist than a single page's configured size
When a client requests the generation list
Then the response contains at most the configured page size
And never the full set of generations in one response
```

### 6.4 Generations with the same creation timestamp still list in a stable order

```gherkin
Given two generations were created with the same recorded creation timestamp
When a client lists generations and repeats the same read
Then the relative order of those two generations is identical every time
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `a generation request without a topic` | `POST /api/v1/generations` body omitting `topic` |
| `volume_pages of 0` / `of 11` | `volume_pages: 0` / `volume_pages: 11` in the request body |
| `requirements text exceeds the maximum length` | `requirements` string longer than 2000 chars |
| `a document type other than "доклад"` | `document_type: "эссе"` (or any non-"доклад" value) |
| `sets a status and an id` | request body includes `status: "completed"`, `id: "<attacker-uuid>"` |
| `sets a created_at timestamp` | request body includes `created_at: "<attacker-chosen-date>"` |
| `exactly 2000 / 2001 Cyrillic characters` | `requirements` field length measured in codepoints, not UTF-8 bytes |
| `the response confirms the generation was created` | `201 Created` with `generation_id`, `status` in body |
| `an entirely Cyrillic topic and requirements` | fixture text with no Latin characters, submitted and read back |
| `idempotency key "key-1"` | `Idempotency-Key: key-1` request header |
| `the response refers to the original generation` | `200 OK` (not `201`) with the same `generation_id` as the first call |
| `already been claimed by a worker` | `arq` job dequeued, `Generation.status` conditionally updated to `in_progress` |
| `redelivered to another worker` | same `arq` job id delivered twice (simulated redelivery in test) |
| `requests its status` | `GET /api/v1/generations/{generation_id}` |
| `no generation exists with a given id` | random UUID never used as a `generation_id` |
| `rejected as permanently invalid` | stub OpenRouter server returns 4xx |
| `fails once with a transient error` | stub OpenRouter server returns 5xx/timeout once, then 200 |
| `keeps failing transiently` | stub OpenRouter server returns 5xx/timeout on every attempt |
| `worker died mid-processing` | `arq` job's lease/heartbeat never updated past its staleness window, no completion write |
| `still legitimately being processed, well within the staleness window` | fixed test clock advanced to just before the staleness threshold |
| `the reconciliation check runs` | the reconciliation sweep's scan-and-sweep pass executes once |
| `completing it at the same moment the sweep considers it stale` | worker's completion CAS and the sweep's failure CAS both attempt to write near-simultaneously in the test |
| `requests the generation list` | `GET /api/v1/generations` |
| `a cursor for the next page` | `next_cursor` field in the list response |
| `paginating with a cursor` | `GET /api/v1/generations?cursor={next_cursor}` |
| `at most the configured page size` | response `items` length ≤ configured `limit` default/max |
| `the same recorded creation timestamp` | two generations inserted with an identical `created_at` value, ordered by the keyset's unique tiebreaker (e.g. `id`) |
