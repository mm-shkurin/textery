## align-design (2026-07-16)

**Surprise:** `simpleMarkToggle`'s 100% line coverage is unearned for `italic` — no test invokes its `run`, yet the line reads green.
**Why:** v8 attributes a hit to the source line, not the closure instance, so one of the five marks sharing the factory's `run:`/`isActive:` lines paints them green for all five.
**Impact:** Factory-extracted behavior makes line coverage blind to per-instance gaps — only a per-instance test is evidence that a given mark works.
