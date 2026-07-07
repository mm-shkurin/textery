# Database Storage Implementation Template

## Rules

- Replace stub implementation with actual logic using SQLAlchemy 2.0 async (`AsyncSession`, `select()`)
- Map between declarative model and domain objects using conversion methods
- Wrap multi-statement write operations in `async with session.begin():`
- Repository classes implement the `Protocol` port defined in `backend/usecase/src/adapters/` — constructor takes an `AsyncSession`

## Reference (read before generating)

- Storage example: `backend/adapters/db/src/access/{feature}/{feature}_storage.py`
- Model example: `backend/adapters/db/src/model/{feature}/{feature}_model.py`
- Migration directory: `backend/adapters/db/migrations/versions/`
- Alembic config: `backend/adapters/db/alembic.ini`, `backend/adapters/db/migrations/env.py`

## SQLAlchemy 2.0 Async Query Examples

| Operation | Code |
|-----------|------|
| Find by field | `result = await session.execute(select(GenerationModel).where(GenerationModel.id == generation_id)); model = result.scalar_one_or_none()` |
| Find many | `result = await session.execute(select(GenerationModel).where(GenerationModel.document_type == doc_type)); models = result.scalars().all()` |
| Create | `session.add(GenerationModel.from_domain(domain)); await session.commit()` |
| Check exists | `result = await session.execute(select(GenerationModel.id).where(GenerationModel.id == generation_id)); exists = result.scalar_one_or_none() is not None` |
| Eager load relation | `select(DocumentModel).options(selectinload(DocumentModel.generation))` |

## Model Conversion

- `model.to_domain()` -- convert SQLAlchemy model to domain object
- `ModelClass.from_domain(domain)` -- classmethod to convert domain to SQLAlchemy model

## Migrations

- Generate: `alembic revision --autogenerate -m "add generations table"`
- Apply: `alembic upgrade head`
- Autogenerate diffs against the declarative `Base.metadata` — every new/changed model must be imported where Alembic's `env.py` collects metadata, or autogenerate will silently miss it.

## Key Paths

- Storage: `backend/adapters/db/src/access/`
- Models: `backend/adapters/db/src/model/`
- Migrations: `backend/adapters/db/migrations/versions/`
