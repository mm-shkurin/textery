## red-acceptance (2026-07-15)

**Expected:** 128/129-code-point multibyte password tests fail RED, needing new production code to measure length in code points instead of bytes.
**Actual:** Both tests pass already-green — `Password._is_valid` uses Python `len(raw_value)`, which counts code points, never UTF-8 bytes.
**Why:** No byte-based length check exists anywhere in the stack (domain or DTO); Python's native `str` length semantics already match the spec.
**Resolution:** Landed the test as a normal (non-skip-marked) regression pin, same treatment as scenarios 2.4/2.4a.
