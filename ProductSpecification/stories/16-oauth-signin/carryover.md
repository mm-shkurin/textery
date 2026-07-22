# Story 16 — carryover (reduced-TDD debt, backend layer)

Written as the work happens, not at the end. Each entry: what was cut, why, and what
restores it. The executable form of this list is
`ProductSpecification/tasks/6-refactoring-oauth-tdd-backfill/progress.md`.

## 2026-07-22 — VK has no credentials

`infra/.env` has `YANDEX_CLIENT_ID` / `YANDEX_CLIENT_SECRET` and nothing for VK. Yandex is
carried end to end; `vk` stays in the contract enum and answers a named configuration error.
Not stubbed, not aliased to Yandex — a stub that looks configured is the exact failure the
tripwire list forbids. Restore: real VK ID credentials, then run the Yandex scenario list
against `vk`.

## 2026-07-22 — redirect URI is not in `infra/.env`

`endpoints.md` says `client_id` / secret / redirect_uri / scopes all come from `infra/.env`
and fail fast at boot. Only the id and secret are there. The redirect URI must match what is
registered in the Yandex OAuth app, so it cannot be invented here — it is read from
`YANDEX_REDIRECT_URI` and boot fails when unset (I7). Needs the real registered value before
the demo can run against live Yandex; the Fake provider path does not need it.

## 2026-07-22 — reduced-TDD ceremony cut across the whole story

Per-step red/green commits collapsed to one commit per scenario. Skipped sub-skills:
`/test-review`, `/test-coverage`, `/refactor`, `/agent-review`, `/premortem`, and the formal
`adapters-discovery` gate. Statements-DSL polish kept minimal. Restore: task 6, one step per
scenario.
