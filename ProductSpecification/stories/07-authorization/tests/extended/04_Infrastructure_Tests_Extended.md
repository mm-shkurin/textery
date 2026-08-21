> These are additional edge case tests. Implement after core tests pass.

# Authorization — Infrastructure Tests (Extended)

Infrastructure is driven only through `infra/docker-compose.yml` and `infra/.env` — never
by hand on a running host.

Shared test data:

| Name | Value |
|---|---|
| Account P (pending) | `qa.infra.pending@textery.test` / `Qa!Infra2026`, active code `042917` |
| Account V (verified) | `qa.infra.verified@textery.test` / `Qa!InfraV2026` |
| Instances | two backend replicas, `backend-a` and `backend-b`, behind the compose-defined proxy |
| Code TTL / lockout cooldown | 10 minutes / the configured lockout window |

---

## TC-07-INFRA-E1 — Clock skew between application instances near a code/lockout expiry boundary

| Field | Value |
|---|---|
| Description | If each replica reads its own system clock, a code is live on one instance and expired on the other, and which answer the user gets depends on load-balancer luck. Deriving both boundaries from the shared database clock makes the outcome instance-independent. |
| Preconditions | Two backend replicas are running against the same Postgres; `backend-a`'s container clock is skewed +45 seconds relative to `backend-b` (e.g. via a faketime shim declared in the compose file — no manual `date` on a host). |
| Test data | Account P's code issued at DB time `T`; verify requests at `T + 9m 40s` DB time, pinned to each replica in turn. Account V locked at `T`, login attempts near the cooldown boundary, likewise pinned to each replica. |
| Steps | 1. Bring up both replicas with the declared skew and confirm it: `docker exec backend-a date` vs `docker exec backend-b date`.<br>2. `POST /api/v1/auth/verify` directly against `backend-a` at the boundary instant, then against `backend-b` with the same state re-seeded.<br>3. Repeat the pair for a locked-out login at the lockout cooldown boundary.<br>4. Read the timestamps the two instances persisted for those decisions. |
| Expected result | Both replicas return the identical status and body for each boundary case — either both `200 OK` `{"is_verified": true}` or both `400 INVALID_OR_EXPIRED_CODE`, and either both `403 ACCOUNT_LOCKED` or both `200 OK` — never one of each; step 4 shows the persisted decision timestamps come from the database clock (they agree to within its resolution) rather than differing by the injected 45-second skew. |
| Status | Not run |
