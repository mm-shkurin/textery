<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — API Tests (Extended)

> **UNBLOCKED 2026-08-19.** §1.1 and §3.1 deferred to «the representation / the outcome the
> contract names» and no contract named one. `endpoints.md` § "The five decisions the test spec
> was blocked on" now records both, and both scenarios below assert the literal outcome.

---

## 1. Field Shapes at the Edges

### 1.1 An omitted, null and empty payload are three inputs with one stored value
```gherkin
Given a visitor with no session
When it reports a site visit with no payload key
And it reports one with an explicitly empty payload value
And it reports one with an empty payload object
Then each is recorded
And each stored payload is the empty object, never an absent value
```

### 1.2 An empty attribution value is stored as absent, not as an empty value
```gherkin
Given a visitor registering with one attribution value present but empty
When it registers
Then that value on the account reads as unset
```

### 1.3 A partial attribution set is frozen as a set, not merged later
```gherkin
Given a browser whose first visit carried only a campaign source
When the visitor later arrives carrying a full attribution set
And it registers
Then the account carries the source from the first visit
And the remaining attribution values read as unset
```

### 1.3a An absent member keeps the set; an unusable member discards it
```gherkin
Given a visitor registering with two attribution values present and three absent
When it registers
Then the two are stored and the three read as unset
Given a visitor registering with four valid attribution values and one over the bound
When it registers
Then all five read as unset
And both registrations succeed identically
```

The two halves are one line apart in the implementation and opposite in outcome. An
implementation that discards the set whenever any member is missing loses attribution for every
link that carries only `utm_source`; one that drops only the offending member writes sets no
marketing link ever produced.

### 1.4 Attribution text outside the basic plane survives the round trip
```gherkin
Given an attribution value combining Cyrillic text and characters outside the basic plane
When a visitor registers carrying it
Then a fresh read returns it unchanged
```

---

## 2. Language and Device Derivation

### 2.1 The highest-priority language tag wins, and it is stored canonically
```gherkin
Given a browser offering several language tags with differing priorities
When it registers
Then the account stores the highest-priority tag
And the stored tag is in its canonical form
```

### 2.2 The same language written three ways is stored one way
```gherkin
Given three browsers offering the same language tag in different letter cases
When each registers
Then all three accounts store the identical value
```

### 2.3 An unrecognised browser is stored as unknown, never as a default
```gherkin
Given a visitor whose browser identifies itself with an unrecognised string
And a visitor whose browser sends no identification at all
When each registers
Then each account's device type and operating system read as unset
And neither reads as the most common device type
```

---

## 3. Occurrence Keys

### 3.1 One occurrence key cannot be reused for a different event
```gherkin
Given a visitor that has reported a site visit
When it reports opening the editor under the same occurrence key
Then the request is refused as a conflicting occurrence
And no second event is recorded
And the first event is not modified
When it reports the same site visit again under that key
Then that request succeeds and still no second event is recorded
```

The last two lines are what separates the conflict from the replay: collapsing a different
event name under a stored key would answer success while silently discarding a real event.

### 3.2 Two visitors reporting the same occurrence key are two events
```gherkin
Given two visitors holding different identities
When both report a site visit under the same occurrence key
Then two events are recorded
```

---

## 4. Ordering Under Load

### 4.1 Many events for one visitor keep a strict, gap-free order
```gherkin
Given one visitor reporting many events in quick succession from several connections
When its events are read in order
Then no two share a position
And the order is the same on every repeated read
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the stored payload is the empty object` | `payload = {}` in a `NOT NULL` column defaulting to `{}` — the decision recorded in `endpoints.md` |
| `refused as a conflicting occurrence` | `409 OCCURRENCE_KEY_CONFLICT`, canonical envelope |
| `characters outside the basic plane` | Astral-plane code points — the fixture that separates byte and code-point bounds |
| `several language tags with differing priorities` | `Accept-Language: ru;q=0.9,en-US;q=1.0` |
| `no two share a position` | Distinct `sequence` values |
