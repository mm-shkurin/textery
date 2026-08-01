> **Implementation Order**: sequential TDD — feed composition → paging & sorting →
> search → input guards → preview & encoding → retry (side-effect guards) → failure
> handling.

# Мои проекты — API Tests

Endpoints: `GET /api/v1/projects` (read), `POST /api/v1/generations/{id}/retry` (write).

## 1. Feed Composition

### 1.1 The feed shows the caller's documents and nothing of anyone else's
```gherkin
Given an authenticated user with documents
And another account with its own documents
When they request their projects
Then only their own documents are returned
And the other account's documents are absent
```

### 1.2 A generation that became a document appears once, as the document
```gherkin
Given a generation the caller converted into a document
When they request their projects
Then the work appears exactly once
And it appears as a document, not as a generation
```

### 1.3 A completed generation with no document is surfaced
```gherkin
Given a generation owned by the caller that completed but was never converted
When they request their projects
Then the generation is present in the feed
And it reports the completed status
```

### 1.4 A failed generation is surfaced and marked retryable
```gherkin
Given a failed generation owned by the caller
When they request their projects
Then the generation is present
And it is marked retryable
```

### 1.5 A generation stuck past the stale threshold is marked recovering and not retryable
```gherkin
Given a generation owned by the caller that has been in progress past the stale threshold
When they request their projects
Then the generation reports the recovering status
And it is marked not retryable
```

### 1.6 Every generation status has a defined feed outcome
```gherkin
Given the caller owns one generation in each known status, some with documents and some without
When they request their projects
Then each generation is either surfaced or suppressed according to the feed rules
And no generation is missing from both the feed and the suppression rule
```

### 1.7 An unrecognized generation status fails closed
```gherkin
Given a generation owned by the caller whose status this contract does not know
When they request their projects
Then the item reports the unknown status
And it is not reported as any displayed status
And its kind is still generation
And a signal is emitted carrying the generation id and the unrecognized value
```

### 1.8 A document and a generation sharing an id are two distinct items
```gherkin
Given a document and a generation owned by the caller that share the same identifier
When they request their projects
Then both are returned as separate items
And they are distinguished by their kind
```

---

### 1.9 The recovering label flips exactly at the stale threshold, in its declared unit
```gherkin
Given the clock is fixed
And a non-terminal generation aged to just before the stale threshold
And a non-terminal generation aged to exactly the stale threshold
And a non-terminal generation aged to just after the stale threshold
When the caller requests their projects
Then only the rows at or past the threshold are reported recovering
And the row just before it is reported running and not retryable
And the classification is computed from the fixed clock, not from a direct system-time read
```

### 1.10 A missing or unparsable stale threshold fails closed
```gherkin
Given the stale threshold is unset, blank or non-numeric
And a non-terminal generation of any age
When the caller requests their projects
Then the row is reported not retryable
And retrying it is refused as a conflict
```

### 1.11 A feed of known statuses emits no unknown-status signal
```gherkin
Given a feed whose generations all carry statuses the contract knows
When the caller requests their projects
Then no unrecognized-status signal is emitted
```

---

## 2. Paging

### 2.1 Paging a static feed returns every row exactly once
```gherkin
Given an authenticated user whose feed spans several pages
When they walk every page in order
Then each item appears exactly once across all pages
And no item is missing
And the number of items collected equals the reported total
```

### 2.2 The reported total counts the deduplicated feed
```gherkin
Given the caller owns documents, orphan generations, and a generation that has a document
When they request their projects
Then the reported total counts the converted work once
```

### 2.3 An empty feed reports a total of zero
```gherkin
Given an authenticated user with no projects
When they request their projects
Then no items are returned
And the reported total is zero
```

### 2.4 A page past the end is empty, not an error
```gherkin
Given an authenticated user with one page of projects
When they request a page beyond the last one
Then no items are returned
And the reported total is unchanged
And the request is not refused
```

### 2.5 The page and its total come from one consistent read
```gherkin
Given an authenticated user with projects
When they request a page while their rows are being modified
Then the returned items and the reported total describe the same snapshot
```

### 2.6 A just-created project is visible to the very next request
```gherkin
Given an authenticated user who has just created a document
When they immediately request their projects
Then the new document is present
```

---

### 2.7 One page costs a fixed number of storage queries whatever the feed's size
```gherkin
Given one account with a small feed and another with a feed many times larger
When each requests one page of the same size
Then the projects repository is invoked the same, constant number of times for both
And the number does not grow with the count of items on the page
```

---

## 3. Sorting

### 3.1 Each sort order returns the feed in that order
```gherkin
Given an authenticated user with projects differing in creation date, edit date, title and type
When they request their projects under each supported sort order
Then each response is ordered by that sort's key
```

### 3.2 Rows sharing a sort key keep a stable order across repeated reads
```gherkin
Given two projects with identical creation timestamps
When the caller requests their projects twice
Then the two rows appear in the same order both times
```

### 3.3 Untitled projects sort last by title
```gherkin
Given the caller owns titled documents and a document with no title
When they request their projects sorted by title
Then the untitled document is last
```

### 3.4 Title ordering does not depend on the database's ambient locale
```gherkin
Given projects whose titles mix upper and lower case, Cyrillic and Latin
When they are sorted by title on a database created with a different default locale
Then the order is identical to the pinned expected sequence
```

### 3.5 Generations are ordered alongside documents, not after them
```gherkin
Given the caller owns documents and orphan generations edited at interleaved times
When they request their projects sorted by edit date
Then generations and documents are interleaved by that date
And no kind is grouped to the end of the feed
```

### 3.6 An unrecognized sort order is refused
```gherkin
Given an authenticated user
When they request their projects with a sort order that is not supported
Then the request is refused as a bad request
And the feed is not returned in the default order instead
```

---

### 3.7 A sort whose key ties across a page boundary returns each row exactly once
```gherkin
Given more projects sharing one document type than fit on a page
And more projects sharing one title than fit on a page
When the caller walks every page sorted by type, then sorted by title
Then each item appears exactly once across the walk
And repeating the walk yields the same items in the same order
```

---

## 4. Search

### 4.1 Search matches title, generation topic and document content
```gherkin
Given the caller owns a document whose title contains a term
And a generation whose topic contains the same term
And a document containing the term only in its body
When they search for that term
Then all three are returned
```

### 4.2 Search is case-insensitive and normalization-stable
```gherkin
Given a document whose title contains a Cyrillic term
When the caller searches for that term in different case and in a different Unicode normalization form
Then the document is returned for every variant
```

### 4.3 Search matches wildcard characters literally
```gherkin
Given the caller owns one document whose title contains a percent sign and others that do not
When they search for the percent sign
Then only the document containing it is returned
```

### 4.4 A whitespace-only query behaves as no search
```gherkin
Given an authenticated user with projects
When they search with a query of only whitespace
Then the full feed is returned
```

### 4.5 Search combines with sorting and paging
```gherkin
Given the caller owns projects matching a search term across several pages
When they request the second page of that search under a non-default sort order
Then the returned items are the second page of the filtered feed in that order
And the reported total is the filtered count, not the unfiltered one
```

### 4.6 Search never crosses account boundaries
```gherkin
Given another account owns a document containing a distinctive term
When the caller searches for that term
Then no results are returned
```

---

### 4.7 Case-folding does not depend on the session's locale
```gherkin
Given a document whose title contains a dotted capital I
When the caller searches for its lowercase form
Then the document is matched under the invariant locale rule
And the result does not change with the database session's ambient locale
```

---

## 5. Input Guards

### 5.1 A page or limit outside its range is refused
```gherkin
Given an authenticated user
When they request their projects with a page below one, a page above the maximum, or a limit outside the allowed range
Then each request is refused as a bad request
And the offending parameter is named by the error code
```

### 5.2 A non-integer page or limit is refused, not truncated
```gherkin
Given an authenticated user
When they request their projects with a fractional, exponential, signed or hexadecimal page value
Then the request is refused as a bad request
And no page is returned
```

### 5.3 A search query over the length bound is refused, measured in code points
```gherkin
Given an authenticated user
When they search with a query at exactly the maximum length in multibyte characters
Then the request succeeds
When they search with a query one character longer
Then the request is refused as a bad request
```

---

### 5.4 A page or limit beyond the integer type is refused, not overflowed
```gherkin
Given a page value larger than the largest machine integer
And a limit value of forty digits
When the caller requests their projects
Then each is refused as a bad request naming the parameter
And no request fails as an internal error or is silently clamped
```

### 5.5 Omitted, empty and repeated parameters have pinned outcomes
```gherkin
Given a request that omits the sort and the query
Then the documented default sort is applied and no search is performed

Given a request that sends the sort empty and the query empty
Then the empty sort is refused as a bad request
And the empty query behaves as no search

Given a request that sends the sort twice with different values
Then the request is refused as a bad request rather than resolved arbitrarily
```

---

## 6. Preview & Output Encoding

### 6.1 The list never returns full document content
```gherkin
Given the caller owns a document with a long body
When they request their projects
Then the item carries a preview no longer than the preview bound
And the full body is absent from the response
```

### 6.2 Preview truncation does not split a character
```gherkin
Given a document whose body has a multi-code-point grapheme at the preview boundary
When the caller requests their projects
Then the preview ends on a whole grapheme
And contains no partial sequence
```

### 6.3 Stored markup is neutralized in every echoed field
```gherkin
Given a document whose title contains markup
And a document whose body contains markup
And a generation whose topic contains markup
When the caller requests their projects
Then the markup is neutralized in the title, the preview and the topic alike
```

### 6.4 Timestamps are returned as UTC instants
```gherkin
Given projects created either side of local midnight in a non-UTC server zone
When the caller requests their projects
Then every timestamp carries an explicit UTC offset
And the two projects are ordered by their true instants
```

---

### 6.5 Multibyte text survives storage and listing unchanged
```gherkin
Given a document title and a generation topic carrying an astral-plane emoji,
  ideographs and a combining accent
When the caller requests their projects
Then each returned string equals the stored one exactly
And no replacement character appears in any field
```

### 6.6 Attacker-controlled values cannot forge a log record
```gherkin
Given a stored generation status and a search query each carrying a line break
  followed by a forged record prefix
When the request is processed
Then each emitted record is a single structured event carrying the value as a field
And no second record parseable on its own is produced
```

---

## 7. Retry — Guards

### 7.1 Retrying a non-existent or foreign generation is refused indistinguishably
```gherkin
Given a failed generation owned by another account
When the caller retries it
Then the request is refused as not found
And the response is byte-identical to retrying an id that does not exist
And no generation is created
```

### 7.2 Retrying a generation that is not failed is refused
```gherkin
Given the caller owns a pending generation, an in-progress one and a completed one
When they retry each
Then every request is refused as a conflict
And no generation is created
```

### 7.3 A missing or oversized idempotency key is refused
```gherkin
Given the caller owns a failed generation
When they retry it with no key, a blank key, or a key over the length bound
Then the request is refused as a bad request
And no generation is created
```

---

### 7.4 Retrying a generation in an unrecognized status is refused
```gherkin
Given a generation whose stored status the contract does not know
When the caller retries it
Then the request is refused as a conflict
And no generation is created
And the source row is unchanged
And the feed reports that row as not retryable
```

---

## 8. Retry — Side-Effect Safety

### 8.1 A retry creates a new generation from the source's stored parameters
```gherkin
Given the caller owns a failed generation
When they retry it
Then a new generation is created carrying the source's parameters
And the caller is its owner
And the source generation is unchanged
```

### 8.2 The failed source stays in the feed beside the new generation
```gherkin
Given the caller has retried a failed generation
When they request their projects
Then both the failed source and the new generation are present
```

### 8.3 A duplicate retry produces one generation (inbound)
```gherkin
Given the caller owns a failed generation
When they retry it twice with the same idempotency key
Then only one generation is created
And both responses describe that same generation
```

### 8.4 A retry whose response was lost creates no second generation (outbound)
```gherkin
Given a retry that reached the server and whose response never arrived
When the client re-sends it with the same idempotency key
Then no second generation is created
And the response describes the generation the first attempt created
```

### 8.5 Concurrent retries across instances produce one generation
```gherkin
Given the caller owns a failed generation
When two retries carrying the same idempotency key arrive at different instances at once
Then exactly one generation is created
And the loser is answered with that same generation
```

### 8.6 One account's key never matches another account's record
```gherkin
Given another account has retried a generation with a given idempotency key
When the caller retries their own failed generation with that same key
Then a generation is created for the caller
And the other account's generation is not returned
```

### 8.7 A fresh key after a terminal outcome starts a new generation
```gherkin
Given the caller retried a failed generation and that retry also failed
When they retry again with a fresh idempotency key
Then a new generation is created
And the request is not answered with the previous attempt
```

### 8.8 The same key against a different source is refused
```gherkin
Given the caller retried one failed generation with an idempotency key
When they retry a different failed generation with that same key
Then the request is refused as a conflict
And no generation is created
```

### 8.9 Retries of one source are capped
```gherkin
Given the caller has retried one failed generation up to the retry ceiling, each with a fresh key
When they retry it once more
Then the request is refused as too many requests
And no generation is created
And the source reports itself as no longer retryable
```

---

### 8.10 Idempotency keys are compared exactly
```gherkin
Given a retry accepted with a given idempotency key
When the same source is retried with a key differing only in letter case
And again with a key differing only in Unicode normalization form
Then each is treated as a distinct key and the outcome matches the byte-exact rule
And a key of multibyte characters at exactly the length bound is accepted,
  measured in code points
```

### 8.11 The retry at the ceiling is accepted and only the next is refused
```gherkin
Given a source generation retried up to one below the retry ceiling
When the caller retries it once more with a fresh key
Then the retry succeeds and a generation is created
And a further retry with another fresh key is refused as too many requests
```

### 8.12 Concurrent retries at the ceiling cannot exceed it
```gherkin
Given a source generation one retry below the ceiling
And two retries with distinct keys held together between the count read and the write
When both proceed
Then exactly one generation is created
And the other is refused as too many requests
And the stored retry count equals the ceiling
```

### 8.13 A retry's generation starts in the initial status, not the source's
```gherkin
Given a failed generation belonging to the caller
When they retry it
Then the created generation is reported pending
And its id, timestamps, owner and lineage are server-assigned
And only its generation parameters are copied from the source
```

### 8.14 A retry that fails on its last write leaves no orphan
```gherkin
Given a retry whose final write fails
When the request returns
Then no generation exists for that key
And no idempotency record survives without its generation
And the source's retry budget is unchanged
```

---

## 9. Create Generation — Newly Enforced Idempotency

### 9.1 A replayed create key returns the existing generation
```gherkin
Given the caller has created a generation with an idempotency key
When they submit the same request again with that key
Then no second generation is created
And the response describes the existing generation
```

### 9.2 Pre-existing generations without a key are unaffected
```gherkin
Given the caller owns generations created before keys were enforced
When they create a new generation with a key
Then it is created
And the older generations remain readable and listable
```

---

### 9.3 The create endpoint ignores server-owned fields and does not rebind on replay
```gherkin
Given a create request whose body also carries an owner, an id, a status and a
  creation timestamp
When it is accepted
Then the stored generation carries server-assigned values for each of them

Given that key replayed with a body naming different generation parameters
Then the stored generation is unchanged
And the response and the enqueued job describe the first body's parameters
```

### 9.4 The deprecated list endpoints keep their behaviour
```gherkin
Given a caller with documents and with generations that carry no idempotency key
When they call the deprecated documents list and the deprecated generations list
Then each returns its previous response shape field for field
And neither requires a new parameter
```

---

## 10. Failure Handling & Disclosure

### 10.1 A query that exceeds the deadline fails generically
```gherkin
Given a projects query that exceeds the statement deadline
When the caller requests their projects
Then the request is refused as unavailable
And the response carries a correlation identifier
And exposes no query text, internal identifier or stack detail
```

### 10.2 The deadline does not leak onto the shared connection
```gherkin
Given a projects request has completed on a pooled connection
When a later long-running query borrows that same connection
Then it is not cancelled at the projects deadline
```

### 10.3 A second concurrent search for one account is shed
```gherkin
Given the caller has a search in flight
When they start a second search before the first completes
Then the second is refused as too many requests
And the first is unaffected
```

### 10.4 A shed slot is released on every exit path
```gherkin
Given a search that ends by exceeding the statement deadline
When the caller searches again
Then the search is accepted
And is not refused as too many requests
```

### 10.5 An abandoned slot is reclaimed
```gherkin
Given a search whose holder stopped without releasing its slot
When the slot's lifetime has elapsed
Then a new search by that account is accepted
```

### 10.6 The feed is not stored by shared caches
```gherkin
Given an authenticated user
When they request their projects
Then the response forbids shared-cache storage
```

### 10.7 A request whose authorization cannot be resolved is denied
```gherkin
Given a request whose token validation cannot complete
When the caller requests their projects
Then the request is denied
And no feed is returned
```

### 10.8 The search slot is held for its whole lifetime and no longer
```gherkin
Given the clock is fixed
And a search whose holder stopped without releasing its slot
When another search by that account starts just before the slot's lifetime elapses
Then it is refused as too many requests
And a search started just after the lifetime elapses is accepted
```

### 10.9 Two searches claiming the slot at once yield exactly one holder
```gherkin
Given two searches for one account held together at the moment of claiming the slot
When both proceed
Then exactly one is accepted
And the other is refused as too many requests
And the losing claim is rejected by the storage layer, not by an in-process check
```

### 10.10 Repeated failures return every acquired resource to baseline
```gherkin
Given the counts of checked-out pooled connections and outstanding search slots
When each refusal path is driven many times over
Then both counts return to their starting values
And neither climbs with the number of failed requests
```

### 10.11 A shed request tells the caller when to retry
```gherkin
Given a request refused as too many requests
Then the response carries a retry-after hint
And the hint is no longer than the search slot's lifetime
```

### 10.12 A caller that gives up leaves no scan running
```gherkin
Given a search whose caller disconnects mid-scan
When the disconnection is observed
Then the database query is cancelled rather than run to completion
And the account's search slot is freed at that moment, not only at its lifetime
```

### 10.13 The correlation id in the response is the one in the log
```gherkin
Given a request that exceeds the statement deadline
When the failure is returned
Then one log record carries the same correlation id as the response
And that record carries the underlying failure detail
```

### 10.14 Each degraded path emits a distinguishable signal
```gherkin
Given a shed search, a request during database unavailability, and a retry whose
  enqueue fails
When each occurs
Then each increments its own named counter, attributed to the account
And an equivalent successful request emits nothing on those channels
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `an authenticated user` | Valid access JWT in the `Authorization: Bearer` header |
| `they request their projects` | `GET /api/v1/projects` |
| `sorted by {key}` | `?sort=created_desc\|created_asc\|updated_desc\|title_asc\|type_asc` |
| `they search for {term}` | `?q={term}` |
| `the retry ceiling` | 5 retries per source generation (`endpoints.md`) |
| `the stale threshold` | `GENERATION_STALE_AFTER_MINUTES`, default 10 |
| `the preview bound` | 200 Unicode code points |
| `the maximum page` | 1000 |
| `they retry it` | `POST /api/v1/generations/{id}/retry` with an `Idempotency-Key` header |
| `refused as a bad request` | 400 with `{error_code, message}` |
| `refused as not found` | 404, byte-identical for absent and foreign |
| `refused as a conflict` | 409 (`NOT_RETRYABLE`, `IDEMPOTENCY_KEY_REUSED`) |
| `refused as too many requests` | 429 (`SEARCH_BUSY`, `RETRY_LIMIT_REACHED`) |
| `refused as unavailable` | 503 `QUERY_TIMEOUT` |
| `forbids shared-cache storage` | `Cache-Control: no-store` |
| `the clock is fixed` | Injected clock pinned to a stated instant; no direct system-time read on the path |
| `the slot's lifetime` | 10 s search-slot TTL |
| `the projects repository` | The `ListProjects` repository port, call-counted |
| `a retry-after hint` | `Retry-After` header on 429 |
| `its own named counter` | A metric named per degraded path (`search_shed`, `db_unavailable`, `enqueue_failed`) |
| `the deprecated documents list` / `generations list` | `GET /api/v1/documents`, `GET /api/v1/generations` |
