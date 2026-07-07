# Red Phase -- Python/pytest Conventions

Universal formats and rules: `.claude/templates/workflow/red-phase-formats.md`

## @pytest.mark.skip Syntax

```python
@pytest.mark.skip(reason="RED: find_by_email returns None")
class TestFindGenerationByEmail:
```

Class-level (adapter tests):

```python
@pytest.mark.skip(reason="RED: PostgresGenerationStorage.find_by_id not implemented")
class TestPostgresGenerationStorageFindById:
```

## Async Test Skip

Async test methods use the same decorator -- `pytest-asyncio` in `auto` mode still collects and skips them normally:

```python
@pytest.mark.skip(reason="RED: RunGenerationUseCase.execute not implemented")
class TestRunGenerationUseCase:
    async def test_should_enqueue_generation_job(self):
        ...
```
