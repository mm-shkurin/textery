# Мои проекты — Integration Tests

The feed itself calls nothing external. «Повторить» does: it re-enters the generation
flow, which reaches the model provider — and it targets exactly the rows the existing
stale-generation sweep already re-runs. That overlap is the integration risk this story
introduces, so it is tested here, not left to the two components' own suites.

---

## 1. Repeat Reaches the Generation Flow

### 1.1 A repeat produces a real generation with the source's parameters
```gherkin
Given a failed generation owned by the caller
When they repeat it
And the provider answers successfully
Then a new generation completes with the source's type, topic, and volume
```

### 1.2 A repeat whose provider call fails leaves a failed generation, not a lost one
```gherkin
Given a failed generation owned by the caller
When they repeat it and the provider returns an error
Then the new generation is recorded as failed
And it appears in the feed as repeatable
```

### 1.3 A repeat whose provider call times out does not hang the request
```gherkin
Given a failed generation owned by the caller
When they repeat it and the provider does not answer
Then the repeat request is answered promptly
And the generation's outcome is reflected in the feed once it resolves
```

---

## 2. Overlap With the Stale-Generation Sweep

### 2.1 A generation being requeued by the sweep is not also repeated
```gherkin
Given a generation the stale sweep is re-running
When the caller requests a repeat of it at the same moment
Then the work runs once
And the caller is told the source is not repeatable
```

### 2.2 A repeat and a sweep tick together produce one run
```gherkin
Given a stale generation
When a repeat and a sweep tick claim it simultaneously
Then exactly one of them wins
And the provider is called once for that work
```

---

## 3. Feed Consistency With the Conversion Flow

### 3.1 A document created from a generation replaces it in the feed
```gherkin
Given a completed generation shown in the feed
When it is converted into a document
And the caller reloads their projects
Then the work is shown once, as the document
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|--------------------------|
| `the provider` | The model provider behind generation (story 1), driven through the existing Fake |
| `repeat it` | `POST /api/v1/generations/{id}/repeat` |
| `the stale sweep` | `backend/usecase/src/generation/requeue_stale_generations.py`, the periodic requeue |
| `claim it simultaneously` | Both paths released at a latch against the same row |
| `the provider is called once` | Call count asserted on the Fake |
| `converted into a document` | `POST /api/v1/documents/from-generation` |
