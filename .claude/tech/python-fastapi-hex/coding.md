# Python/FastAPI/Hexagonal Coding Idioms

Tech binding for `coding-rules.md`. Shared section structure: `.claude/templates/coding/coding-sections.md`.

## Deployment

- In-memory state to avoid: module-level `dict`/`set`, mutable default arguments, singleton caches in closures, class-level mutable attributes, `lru_cache`d functions that memoize per-request data.
- The backend runs behind `uvicorn`/`gunicorn` with multiple worker processes — never rely on process-local state (an in-memory job status dict, a module-level counter) to survive across requests. Redis (via `arq`) or PostgreSQL are the only valid shared state stores.

## Clean Architecture

- `domain`: pure Python — no FastAPI imports, no Pydantic, no SQLAlchemy decorators.
- `usecase`: ports are `Protocol` classes (or `abc.ABC` if runtime `isinstance` checks are ever needed — prefer `Protocol`). No framework code except `async`/`await` itself.
- `adapters/rest`: FastAPI routers (`APIRouter`), Pydantic request/response models, FastAPI `Depends()`.
- `adapters/db`: SQLAlchemy 2.0 async engine, declarative models, Alembic migrations.
- `adapters/email`: mail-sending adapters (mocked for now — see product decisions; kept as a real module for when a sender is wired).
- `adapters/scheduling`: `arq` task functions and worker settings — background job execution for generation requests.
- `adapters/security`: JWT issuing/verification, OAuth (Yandex ID, VK ID) token exchange — needed from story 7 onward.
- `application`: FastAPI app instance, `container.py`/`bootstrap.py` composition root, `arq` `WorkerSettings`.

## Domain-Driven Design

- Validation: throws `ValidationException` (custom domain exception).
- Enum: `enum.Enum` or `StrEnum`. `parse(value: str)` classmethod, `.value` for lowercase.
- Optional: `Optional[T]` / `T | None`. Collections: `tuple`/`frozenset` (immutable), `list` (mutable). Adapters convert `None`.
- Forbidden dispatch: `isinstance`. Adapters dispatch from Pydantic/SQLAlchemy models.
- Typed list: `list[ArchivedTask]` not `list[BaseProtocol]` + `isinstance`.
- Parameter object: `dataclass` or `NamedTuple`.
- Immutable: `@dataclass(frozen=True)`. Transitions via `dataclasses.replace()`.

## Code Generation

- `@dataclass` for domain DTOs/VOs. `@dataclass(frozen=True)` for immutable.
- DI: manual `__init__` wiring, resolved via FastAPI `Depends()` provider functions defined in the composition root. No DI framework (`dependency-injector` etc.).
- Builders: class methods (`create`, `of`, `from_`).

## Naming

- Persistence: `{Name}Model` (SQLAlchemy declarative class). Converters: `to_dto()` / `to_model()` / `to_domain()`.
- REST DTOs: `{Feature}RequestDto` / `{Feature}ResponseDto` — plain Pydantic `BaseModel` subclasses, distinct from domain dataclasses.
- Modules: `snake_case`.

## Immutability

- `frozen=True` dataclasses, `tuple` over `list`, `frozenset` for sets.
- Pydantic request/response models: `model_config = ConfigDict(frozen=True)` where the DTO has no reason to mutate after construction (most request/response DTOs).

## Accessor Chains

- `a.b.c.format()` → convenience property `a.c_value`.

## Optional/None Handling

- `match/case` or ternary — never `if x is not None: return x.value`.
- `or` for defaults, conditional expressions for mapping.

## Null Boundary

- Routers: `or None` / explicit checks before building DTOs.
- Request dataclasses: `field(default=None)` typed as `Optional[T]`.
- Pydantic request models: optional fields declared `field: T | None = None`.

## Request DTO Conversions

- Examples: `str` date → `datetime`, `str` → enum parse.
- Methods: `to_timestamp()`, `parsed_action_type()`.

## Branching

- `match/case` over `if/return` chains (Python 3.10+).

## Controllers

- `to_usecase_request()` on request DTO.
- FastAPI route handlers are `async def`. Status codes are declared on the route decorator (`@router.post("/generations", status_code=201, response_model=GenerationResponseDto)`) or built explicitly: `JSONResponse(content, status_code=200)` → 200, `status_code=201` → 201, `Response(status_code=204)` → 204.
- Errors via a centralized `@app.exception_handler(DomainException)` registered in the composition root — never `try/except` per route.

## Storage Adapters

- SQLAlchemy models ≠ domain. `@classmethod from_domain(cls, domain)` + `to_domain()`. Never expose SQLAlchemy models outside the `adapters/db` module.
- Async session per request/job: `AsyncSession` injected via `Depends(get_session)` (REST) or created per `arq` job (scheduling).
- No manual row-dict grouping or `itertools.groupby()` — use SQLAlchemy relationship loading (`selectinload`, `joinedload`) for joins.
- Trivial: `result = await session.execute(select(GenerationModel)); return [m.to_domain() for m in result.scalars().all()]`.
- Query objects: `dataclass` with fields for building `select()` filter clauses when a query has more than a couple of conditions.

## Refactor Agent — Python Terms

| Generic term (in agent) | Python equivalent |
|--------------------------|-------------------|
| Qualified enum references in logic | `from module import EnumValue` |
| Type-checking/type dispatch in domain or usecase | `isinstance`, `type()` checks |
| Base-type list re-partitioned with type checks | `list[BaseProtocol]` + `isinstance` |
| Immutable data class | `@dataclass(frozen=True)` |
| Collection pipeline terminal operation | `list()` / comprehension terminal |
| Manual per-field assertion for immutable data types | Applies to frozen dataclasses and value objects |

## Scan Checklist — Storage Grep Patterns

| # | Grep pattern / indicator |
|---|--------------------------|
| A33 | `itertools.groupby`, `defaultdict(list)`, `dict[..., list[...]]`, Row/Projection classes |
| A34 | Count `AsyncSession`/repository references per storage class |
| A42 | Static/class methods returning `select()` fragments or `Query` objects built from filter params |
| A43 | Raw `session.execute(text(...))`, manual column extraction from `Result.tuples()` |
| A44 | `select().where()` chains >5 lines inline |

## HTTP Clients

- Production: `httpx.AsyncClient` (async) for OAuth provider calls (Yandex ID, VK ID); the `openai` Python SDK's async client (`openai.AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)`) for generation calls, since generation goes through **OpenRouter** (OpenAI-compatible gateway, gives access to Claude and other models through one client — chosen so story 6's per-tariff model switching is just a `model` string change, not a new vendor adapter) rather than the native Anthropic API. Tests: `unittest.mock`/`pytest-mock` at the adapter boundary — never hit the real OpenRouter endpoint or OAuth providers in usecase/adapter tests.

## Error Handling

- Domain: `DomainException(Exception)`. Bubble to a centralized FastAPI exception handler registered in `application`'s composition root.
