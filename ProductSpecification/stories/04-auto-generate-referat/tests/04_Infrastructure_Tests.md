# Auto-generate: реферат — Infrastructure Tests

**n/a for this story.**

Infrastructure tests cover database-connection failure, recovery after failure, and
external-service unavailability. All three are properties of the generation path story 1
built, and this story changes none of them: no new service, no new container, no new
connection, no new environment variable, no migration.

The one thing that moves is where the prompt string is composed — from the provider
adapter into the domain. That is a pure function with no I/O, so no infrastructure
failure mode reaches it.

The provider's behaviour when GigaChat is unavailable is covered by
`06_Integration_Tests.md` rather than here, because what matters for this story is that
the hand-off did not disturb the existing failure handling.

Set `Infra = n/a` for this story in `stories.md`.
