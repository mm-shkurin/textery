# Acceptance Test Implementation (Green Phase) -- Python/FastAPI/Hexagonal

> Universal workflow: `.claude/templates/tdd/green-acceptance.md`

## Tech-Specific Details

- **Disable marker**: `@pytest.mark.skip` decorator -- remove to enable, re-add on failure
- **Test target**: `{test_file_name}` (file name for pytest `-k` filter)
- **Error terminology**: "FastAPI exception handler" (the centralized `@app.exception_handler` registered in the composition root)
