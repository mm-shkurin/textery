# Scenario 3.2 — The exchange is issued exactly once per code

## red-frontend (2026-07-22)

**Quirk:** vitest renders an anonymous `vi.fn()` mock in assertion messages by its factory label `vi.fn()`, not by the exported symbol name — the red prediction's first revision said `expected "saveSession" to be called 1 times` and mismatched on Message alone; revision 2 using the `vi.fn()` label matched literally.
**Where:** frontend/src/features/auth/components/__tests__/ mocks of `saveSession`/`navigate`/`oauthExchange`.
**Implication:** any red prediction quoting a call-count failure against these seams must write the label as `vi.fn()`, else the Message field will spuriously read NO on an otherwise-correct prediction.
