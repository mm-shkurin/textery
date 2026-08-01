# Story 4: Auto-generate: реферат — Backend Progress

Owns Backend, Integration, Security, Load and Infrastructure Scenarios (acceptance steps
inline per scenario). Narrative and decisions live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

Scenario 1.1 starts the story because the prompt builder is a pure domain component: it
needs no adapter, no database and no stub, so the first work unit is the smallest one
that can be red.

## Backend Scenarios (tests/01_API_Tests.md)

### Scenario 1.1: A реферат prompt asks for the реферат structure
- [S] red-acceptance — the prompt has no black-box surface. The acceptance layer is
  HTTP-only with no compile dependency on `backend/` (no file under `acceptance/`
  imports it). No endpoint returns the prompt: `POST /api/v1/generations` returns
  `generation_id`/`status`/`created_at` plus echoed request fields, `GET
  /api/v1/generations/{id}` returns status and content — and Security scenario 2.1 of
  this same story requires the prompt not be written verbatim even to the log. The
  outbound side is no better: the DSL table's GigaChat stub server does not exist
  (`acceptance/conftest.py` has no provider-stub fixture; `gigachat_provider.py` posts
  to a module-level `COMPLETIONS_URL` on the live Sber host). The spec's own DSL settles
  it — "the prompt is built for it" is a direct in-process call on a pure domain
  component. Covered by `red-usecase` / `green-usecase` below.
- [~] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [S] green-acceptance — nothing to turn green; see `red-acceptance` above.

### Scenario 1.2: A реферат prompt forbids a bibliography
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.3: A доклад prompt is unchanged by the move into the domain
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.4: Every supported document type yields a prompt
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.5: The topic cannot displace the template's instructions
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.6: Requirements and extra wishes cannot displace the instructions either
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: The provider sends the prompt it was given
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: A реферат request is accepted
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: A реферат generation completes end to end
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.3: An unsupported document type is still rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.4: A duplicate submission does not generate twice
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Integration Scenarios (tests/06_Integration_Tests.md)

### Scenario 1.1: The реферат prompt reaches the provider
- [ ] red-integration
- [ ] green-integration

### Scenario 1.2: The provider's document becomes the generation's content
- [ ] red-integration
- [ ] green-integration

### Scenario 2.1: A provider error still ends the generation as failed
- [ ] red-integration
- [ ] green-integration

### Scenario 2.2: A provider timeout still ends the generation as failed
- [ ] red-integration
- [ ] green-integration

### Scenario 2.3: A malformed provider body still ends the generation as failed
- [ ] red-integration
- [ ] green-integration

## Security Scenarios (tests/05_Security_Tests.md)

### Scenario 1.1: A hostile topic does not take over the generation
- [ ] red-security
- [ ] green-security

### Scenario 1.2: Every user-controlled field is treated as data
- [ ] red-security
- [ ] green-security

### Scenario 2.1: The prompt is not written to the log verbatim
- [ ] red-security
- [ ] green-security

### Scenario 2.2: A provider failure does not leak its raw body
- [ ] red-security
- [ ] green-security

### Scenario 3.1: A disabled card does not close the API
- [ ] red-security
- [ ] green-security

## Load Scenarios

- [S] n/a — the story exercises no operation belonging to the project's Throughput
  profile that story 1 does not already cover. Reasoning in `tests/03_Load_Tests.md`.

## Infrastructure Scenarios

- [S] n/a — no new service, container, connection, environment variable or migration;
  the moved prompt builder performs no I/O. Reasoning in
  `tests/04_Infrastructure_Tests.md`.
