# AI chat editing — Infrastructure Tests

This story adds a worker process, a queue broker and long-lived HTTP responses. Each is a
new way for the deployment to be wrong while the code is right.

---

## 1. Datastore availability

### 1.1 A datastore outage refuses edits cleanly instead of hanging
```gherkin
Given the datastore is unavailable
When a user submits an instruction
Then the request is refused with a server error within the configured timeout
And the response carries no internal detail
```

### 1.2 Edits work again after the datastore recovers, with no state left behind
```gherkin
Given the datastore was unavailable and has recovered
When a user submits an instruction
Then it is accepted and reaches a terminal state
And no edit left non-terminal by the outage remains non-terminal past its deadline
```

---

## 2. Queue broker availability

### 2.1 A broker outage does not accept edits that will never run
```gherkin
Given the queue broker is unavailable
When a user submits an instruction
Then either the request is refused
Or the edit is recorded and later executed once the broker recovers
And in neither case is the user shown a running edit that no worker will pick up
```

### 2.2 A worker started against a recovered broker drains the backlog without a stampede
```gherkin
Given a backlog of edits accumulated during a broker outage
When the worker resumes
Then the backlog is drained in bounded batches
And provider calls stay within the downstream rate limit
And the retries are not all attempted on the same tick
```

---

## 3. Configuration and proxy

### 3.1 Missing or invalid configuration fails at startup, in both processes
```gherkin
Given the configuration is missing or invalid for <setting>
When the web process starts
Then it fails to start with a message naming the setting
And the worker process fails the same way
```
Cover each setting separately, unset and blank: context-fit threshold, daily quota, edit
deadline, queue broker address, edit-provider selection, worker concurrency, downstream
provider rate limit, provider connect and read timeouts, client timeout, list page cap,
event retention bound, maximum document length, maximum instruction length, database pool
bound, canonical quota timezone. Every value the story's behaviour depends on fails the
boot; a value that silently falls back to a development default is the incident.

### 3.2 A non-development environment refuses to boot with the fake edit provider
```gherkin
Given the environment is not a development environment
And the edit provider is configured as the fake
When either process starts
Then it fails to start
```

### 3.3 The timer ordering invariant is validated at startup
```gherkin
Given a configuration where the provider timeout multiplied by its retry count is not
  less than the edit deadline
When either process starts
Then it fails to start naming the violated ordering
```
Also assert the deadline-versus-proxy-timeout and client-timeout-versus-deadline orderings,
each with the units stated in seconds.

### 3.4 The proxy streams the first chunk before the response completes
```gherkin
Given the deployed proxy configuration from the repository
When a client reads an edit's event stream through the proxy
Then the first chunk is observed before the response has completed
And the connection is not closed before the edit deadline
```
This asserts response buffering is disabled and the read timeout exceeds the edit
deadline — declared in `infra/`, never hand-edited on a host.

### 3.5 A silent stream is kept alive rather than dropped
```gherkin
Given an edit whose provider emits nothing for longer than the proxy idle timeout
When a client reads the stream through the deployed proxy configuration
Then keep-alive traffic is observed on the connection
And the connection is still open when the first chunk finally arrives
```
The keep-alive interval being shorter than the proxy idle timeout is a startup-validated
ordering, alongside the deadline orderings in 3.3. Without it the client merely enters its
reconnect state — which every other scenario asserts *works* — so the suite stays green
while every long edit looks broken to the user.

---

Hazard-scan guards continue in `04_Infrastructure_Tests_Guards.md`.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the datastore is unavailable` | Database container stopped or connections refused |
| `the queue broker` | Redis instance backing the edit queue |
| `the worker process` | The arq worker entry point |
| `the deployed proxy configuration` | nginx configuration under `infra/` |
| `the edit deadline` | Env-configured maximum lifetime of one edit |
