---
name: test-acceptance
description: Run acceptance tests (backend API, frontend UI, or load suite). Use when user wants to run E2E acceptance tests or mentions /test-acceptance command.
---

# Run Acceptance Tests

## Pre-Checks

Read ports from `infra/.env` and verify required services are up **before** running tests.

### Backend (always required)

Check the health endpoint (see `technology.md` Conventions table for path):
```bash
source infra/.env && curl -s -o /dev/null -w "%{http_code}" http://localhost:$BACKEND_PORT{health_endpoint} 2>/dev/null || echo "UNAVAILABLE"
```

- `200` → OK.
- `UNAVAILABLE` or non-200 → start backend first: `Skill tool: skill="run-backend"`. Wait for startup.

### Frontend (required when argument is `frontend` or a frontend test class)

```bash
source infra/.env && curl -s -o /dev/null -w "%{http_code}" http://localhost:$FRONTEND_PORT 2>/dev/null || echo "UNAVAILABLE"
```

- `200` → OK.
- `UNAVAILABLE` or non-200 → start frontend first: `Skill tool: skill="run-frontend"`. Wait for startup.

### Load

No load suite is implemented in this project yet — `acceptance/pytest.ini` only
defines `backend`/`frontend` markers, and no load-baseline image/container mechanism
exists under `infra/`. If the argument is `load`, **stop and tell the user**: point
them at `ProductSpecification/stories/01-auto-generate-doklad/tests/03_Load_Tests.md`
(the planned scenarios) instead of running anything.

## Action

Acceptance tests run via `pytest` against the `acceptance/` module (see
`ProductSpecification/technology.md` Conventions table).

- `backend` → `pytest acceptance/ -m backend`
- `backend {ClassName}` → `pytest acceptance/ -k {ClassName} -m backend`
- `frontend` → `pytest acceptance/ -m frontend`
- `frontend {ClassName}` → `pytest acceptance/ -k {ClassName} -m frontend`
- `{ClassName}` → `pytest acceptance/ -k {ClassName}`
- (no args) → `pytest acceptance/`

**Always pass the test class name** when running a specific test — never run the full suite just to check one test.

## Execution Strategy

Read `.claude/guidelines/tdd-rules.md` and follow its "Stop on first failure" protocol:

1. **Launch in background:** `run_in_background: true` — note the output file path from the result. Store `SEEN=0` to track lines already shown.
2. **Poll with separate Bash calls:** Make repeated **individual** Bash calls (NOT a loop inside one call — that hides output until the loop finishes). Each call checks for new lines and the terminal signal:
   ```bash
   TOTAL=$(wc -l < "$OUTPUT" 2>/dev/null || echo 0) && sed -n "$((SEEN+1)),${TOTAL}p" "$OUTPUT" | grep -E "PASSED|FAILED|ERROR|passed|failed|error" ; grep -c -E "= [0-9]+ passed|= [0-9]+ failed|= [0-9]+ error" "$OUTPUT" 2>/dev/null && echo "DONE" || echo "RUNNING"
   ```
   After each call: update SEEN, check if DONE, if still RUNNING wait ~5s then call again. Repeat until DONE or task completes.
   **CRITICAL:** Each check must be a separate tool call so the user sees output immediately.
3. **If pytest summary shows only `passed`** → read output file, report pass counts. Done.
4. **If any `failed`/`error`** → stop suite (`TaskStop`), then **immediately disclose to the user**:
   > "Stopped after the first failure. N tests passed, 1 failed, M tests did not run — there may be additional failures in the remaining tests."
   Calculate M from total test count minus passed minus failed. **Never present a stopped-early run as if it were a complete run.** Then: read stack trace from the output file, investigate root cause. Do NOT collect further failures.
   - **Collection error** (pytest fails before running any test — import/fixture error) → read error lines, report immediately. No need to check infrastructure.
   - **Infrastructure error** (`WebDriverException`, `Connection reset`) → re-check backend/frontend health.
   - **Application error** (assertion failure, wrong status) → investigate and fix.
   - **NEVER dismiss a failure as "not related", "pre-existing", or "from another story".** Every failure is your problem right now. Either fix the root cause or create a task with `/task` — but never report results and move on while the build is red.

## Output

Report the test results from output. Always include pass/fail counts and how many tests did not run (if stopped early). If any test failed and you could not fix it, create a task to track the fix — do not leave failures untracked.
