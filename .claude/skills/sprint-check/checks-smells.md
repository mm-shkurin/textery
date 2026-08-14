# Criterion 3 — Source quality, security, tests

The question behind every item: **would a reviewer reading this code cold find
something that is hard to change, unsafe, or untrustworthy?**

Mechanical probes: categories `smell`, `security`, `tests`
(`probes/rules_quality.py`). Size and complexity smells that need judgment go to a
review agent — a grep cannot decide whether a class is a God Object.

## Configuration and hardcoding (`smell`)

| Item | What is checked | Lane |
|---|---|---|
| External endpoints | No provider URL, host, or region baked into source — configuration supplies it, with no working default | `SMELL-URL` |
| Filesystem coupling | Certificates, keys, and asset paths are configured, not resolved relative to a package directory | `SMELL-FS-PATH` |
| Magic numbers | Timeouts, intervals, limits, and sizes come from configuration | `SMELL-MAGIC` |
| Policy as data | Allow/deny lists (sanitizer tags, permitted types, feature flags) are data a change of policy can edit without touching code | `SMELL-POLICY-IN-CODE` |
| Route literals | API paths come from one route map, not string literals at call sites | `SMELL-ENDPOINT-LITERAL` |
| Type escapes | No casts or ignore pragmas that silence the type system instead of fixing the type | `SMELL-TYPE-ESCAPE` |
| Leftovers | No commented-out code, no stale TODO/FIXME piles, no dead exports | `SMELL-DEAD-CODE` + judgment |

## Structure (judgment lane)

| Item | What is checked |
|---|---|
| God object | No class or module that searches, filters, writes, versions, and updates at once |
| Long method | No entry-point method carrying the whole flow; branching by status belongs to a state machine |
| Single responsibility | An entity does not simultaneously own naming, validation, and export rules |
| Duplication | Repeated construction/setup is a factory, fixture, or parametrized case |
| Abstraction level | One function does not mix orchestration with byte-level detail |
| Component responsibility | A UI container does not own selection, generation, navigation, and modals at once |
| Transport abstraction | Callers depend on a typed result, not on the raw response shape |
| Data freshness | Repeat navigation does not refetch blindly; mutations update the cache locally rather than forcing a full reload (`SMELL-REFETCH-TOKEN` catches the counter form) |
| Push vs poll | Long-running progress is pushed or backed off, not polled at a fixed interval (`SMELL-POLLING` catches the naive form) |
| Lifecycle | In-flight requests are cancelled on unmount; timers derive from a timestamp so they cannot desync (`SMELL-NO-ABORT` catches the missing primitive) |

## Security (`security`)

Report these first, whatever the criterion's score.

| Item | What is checked | Lane |
|---|---|---|
| Secrets | No credentials, keys, or tokens in tracked source or history | `SEC-SECRET` + judgment (`git log -S`) |
| Credential storage | Session credentials are not in XSS-readable web storage | `SEC-WEB-STORAGE` |
| HTML sinks | No unsanitized HTML rendering path, now or via a plugin one commit away | `SEC-RAW-HTML` |
| Dynamic execution | No `eval`, shell interpolation, or unsafe deserialization | `SEC-EVAL` |
| Transport safety | TLS verification and origin policy are not disabled wholesale | `SEC-TLS-OFF` |
| Server-side fetching | Renderers and parsers deny remote resources by default (SSRF) | `SEC-FETCHER` |
| Input validation | Every external input is validated at the boundary it enters | judgment |

## Tests (`tests`)

| Item | What is checked | Lane |
|---|---|---|
| Presence | The layer has tests at all | `TEST-PRESENT` |
| Honesty | Nothing skips silently on a fresh checkout; a skipped suite is a failing suite that looks green | `TEST-SKIPS` |
| Bounded | Tests taking locks or racing have timeouts, so a deadlock fails fast instead of hanging the run | `TEST-TIMEOUT` |
| Assertions | Assertions are strict and meaningful; no test depends on another's order | judgment (`/test-review`) |
| Automation | The suite runs in CI on every push | judgment |

## Infrastructure

| Item | What is checked | Lane |
|---|---|---|
| Portability | Serving, proxying, and TLS are part of the containerized stack in the repo, not hand-configured on a host — a new machine must be reproducible from `infra/` alone | judgment |

## Known instances (2026-08-07)

Hardcoded provider auth/generation URLs; package-relative certificate path; God-object
storage class; 65-line use-case method; entity mixing naming, validation, and export;
hardcoded sanitizer allow-list; renderer able to fetch remote images (SSRF); lock test
without timeout; duplicated JWT test setup; host-level nginx outside Docker; no query
cache; manual polling; tokens in `sessionStorage`; markdown renderer one plugin away
from raw HTML; `as unknown as` in fixtures; overloaded flow component; transport shape
leaking into hooks; reload-counter refetch; literal endpoint paths; missing request
cancellation; countdown timer able to desync.
