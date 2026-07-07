# Open questions

- **Cloud provider**: not decided. When it is, confirm whether `terraform-yandex`
  applies (Yandex Cloud) or a different/generic IaC agent is needed. Until then,
  `terraform-yandex` and any other cloud-specific agent stay dormant.
- **CI/CD platform**: not chosen yet.
- ~~Resources provisioned for local dev~~ — **resolved 2026-07-06**: added
  `infra/docker-compose.yml` (backend, worker, postgres, redis, frontend). See
  `./architecture.md` for topology. `backend`/`worker`/`frontend` still run on
  TEMP placeholder Dockerfiles pending real application code from separate
  sessions — that swap is documented in `architecture.md`, not tracked here as
  a further open question.
