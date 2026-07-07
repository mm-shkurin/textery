# Scheduling Adapter Implementation Template (arq)

## Product Context

This is the adapter that makes generation asynchronous (see `ExpectedLoad.md`): a REST
request enqueues a job and returns immediately with a generation ID; an `arq` worker
process picks the job up and runs the actual Anthropic API call. Two distinct patterns
live here:

1. **One-off enqueued jobs** (the main pattern -- e.g. "run this generation").
2. **Periodic/cron jobs** (occasional -- e.g. a future cleanup job), via `arq`'s `cron()`.

## Rules

- The usecase defines a `JobQueue` port (`Protocol`, `async def enqueue(...)`). The
  `arq`-backed adapter implements it by calling `ArqRedis.enqueue_job(...)`.
- The actual work (the task function registered in `WorkerSettings.functions`) delegates
  immediately to a usecase -- no business logic in the task function itself.
- Task functions receive the `arq` job context (`ctx`) first, then job arguments; they
  resolve the usecase from the composition root (`ctx["container"]`, wired in
  `on_startup`).
- `arq` itself is Redis-backed and only ever processes a job once across however many
  worker instances are running -- no separate distributed-lock mechanism is needed for
  one-off jobs. Only add a lock (e.g. a `pg_advisory_lock`) for `cron()` jobs, where
  every worker instance would otherwise fire the same schedule independently.

## Reference (read before generating)

- Job queue port: `backend/usecase/src/adapters/job_queue.py`
- Arq adapter: `backend/adapters/scheduling/src/arq_job_queue.py`
- Task functions: `backend/adapters/scheduling/src/tasks/{feature}_task.py`
- Worker settings: `backend/adapters/scheduling/src/worker_settings.py`
- Usecase invoked by the task: `backend/usecase/src/{feature}/{feature}_usecase.py`

## Pattern (One-Off Job)

1. Usecase calls `await self.job_queue.enqueue("generate_document", generation_id=generation.id)`
2. `ArqJobQueue.enqueue()` implementation: `await self.redis.enqueue_job(job_name, **kwargs)`
3. Task function in `tasks/generation_task.py`:
   ```python
   async def generate_document_task(ctx: dict, generation_id: str) -> None:
       usecase: RunGenerationUseCase = ctx["container"].run_generation_usecase()
       await usecase.execute(RunGenerationRequest(generation_id=generation_id))
   ```
4. Register in `WorkerSettings.functions = [generate_document_task]`

## Pattern (Cron Job)

1. Define with `arq.cron(coroutine, hour={3}, minute={0})` in `WorkerSettings.cron_jobs`
2. Acquire a DB-based advisory lock at the top of the coroutine before delegating to the usecase, release in a `finally` block
3. Delegate to usecase: `await usecase.execute()`

## Configuration

Add to environment config (`backend/adapters/scheduling/src/scheduling_config.py`, read via `pydantic-settings`):
```
ARQ_REDIS_URL=redis://localhost:6379/0
ARQ_MAX_JOBS=10
ARQ_JOB_TIMEOUT=300          # generation jobs must not hang forever on a stuck LLM call
```

## Key Paths

- Ports: `backend/usecase/src/adapters/`
- Adapter + tasks: `backend/adapters/scheduling/src/`
- Worker entrypoint: `backend/adapters/scheduling/src/worker_settings.py`
