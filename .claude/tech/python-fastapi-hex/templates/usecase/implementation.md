# Usecase Implementation Template -- Python/FastAPI/Hexagonal

> Universal rules: `.claude/templates/tdd/green-usecase.md`

## Tech-Specific Details

- Not-implemented marker: `raise NotImplementedError()`
- Domain path: `backend/domain/src/`
- Adapter interfaces (ports) path: `backend/usecase/src/adapters/` — defined as `Protocol` classes
- Usecases with `async` ports (repository, LLM client, job queue) are themselves `async def execute(...)`

## Reference (read before generating)

- Usecase example: `backend/usecase/src/{feature}/{feature}_usecase.py`
- Adapter interface: `backend/usecase/src/adapters/`
- Fake implementation: `backend/usecase/tests/fake/{feature}/fake_{feature}_storage.py`

## Key Paths

- Production: `backend/usecase/src/{feature}/`
- Tests: `backend/usecase/tests/{feature}/`
- Fakes: `backend/usecase/tests/fake/`
