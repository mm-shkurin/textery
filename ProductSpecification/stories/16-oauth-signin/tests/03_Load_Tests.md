# OAuth sign-in — Load Tests

**Load = n/a.**

Per the relevance filter in `test-spec-format.md`: OAuth sign-in is a one-shot per-user
authentication action (login-class), whose lifetime volume is bounded by user count. It
does not exercise the project's **Throughput** Load Challenge Profile (`ExpectedLoad.md`) —
there is no high-rate generation-style endpoint here and no scaling DB query.

Abuse-rate concerns (hammering `start` / `callback` / `exchange`) are covered as a
**rate-limiting security scenario** (`05_Security_Tests.md` §5.1), not as a throughput load
test.
