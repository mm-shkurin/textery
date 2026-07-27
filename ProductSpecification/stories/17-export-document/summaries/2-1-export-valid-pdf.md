# Scenario 2.1: A document exports as a valid PDF — Journey Summary

## green-adapter rendering (2026-07-27)

**Quirk:** `import weasyprint` fails on the Windows dev host (no GTK/Pango/cairo), so a host-side pytest cannot even COLLECT a rendering-adapter test that imports the module at load; and a module-level `pytest.importorskip("<dep>")` will SKIP FOREVER in CI — indistinguishable from a pass in the summary — unless the dep is actually in `backend/requirements.txt` and installed on the runner.
**Where:** backend/adapters/rendering (weasyprint_pdf_renderer.py, its tests, backend.Dockerfile, both CI ci.yml `test` jobs).
**Implication:** Run rendering-adapter red/green tests in the Linux backend container (`docker compose exec`, `PYTHONPATH=domain/src:adapters/rendering/src:...`); add every render dep to requirements + BOTH CI test jobs so the importorskip resolves and the test RUNS in the gating env; never lift a RED skip into a permanent `skipif(unimportable)`.

## green-acceptance (2026-07-27)

**Quirk:** Docker Desktop was down at the green-acceptance step; the in-container acceptance run is hard-blocked until the engine is up — the loop resumed automatically via a Monitor polling `docker info`.
**Where:** infra/docker-compose.yml backend service (baked image).
**Implication:** green-acceptance / in-container steps depend on a running Docker engine; a down engine is a stop-and-wait, not a failure.
