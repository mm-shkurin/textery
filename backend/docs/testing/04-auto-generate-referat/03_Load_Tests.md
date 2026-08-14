<!-- COPIED FILE. Source of truth: ProductSpecification/stories/04-auto-generate-referat/tests/03_Load_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: реферат — Load Tests

**n/a for this story.**

The project's declared Load Challenge Profile is **Throughput** (`ExpectedLoad.md`):
request rate, queue depth, worker concurrency, and downstream GigaChat rate limits.

This story changes none of them. It adds no endpoint, no queue, no worker, and no call —
generation continues to run through the same async path story 1 built, at the same rate.
The only measurable change is a longer prompt, which raises input tokens per call and
leaves requests-per-second untouched.

The throughput of the generation endpoint is worth load-testing; it belongs to story 1,
whose scenarios cover the path this story reuses unchanged. Duplicating them here would
assert story 1's behaviour under story 4's name.

Set `Load = n/a` for this story in `stories.md`.
