# Manual input mode (non-AI document creation) — Integration Tests

n/a — this story has no external system integration. No LLM/generation provider call,
no OAuth, no third-party API of any kind (that's the entire point of the manual/non-AI
path — see `05_ManualMode_Notes.md`, Integration Notes). Document create/read/save are
plain calls against the project's own database, already covered by
`01_API_Tests.md` and `04_Infrastructure_Tests.md`.
