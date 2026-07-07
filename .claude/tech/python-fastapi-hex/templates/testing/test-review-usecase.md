# Test Review Patterns: Usecase Layer (Python/FastAPI)

Python/pytest code examples for usecase test anti-patterns. For universal rules: `.claude/templates/testing/test-review-patterns.md`

## Python-Specific Rules (Usecase)

1. **Use descriptive assertion messages** -- add a second argument to `assert` or use pytest's built-in introspection for clear failure messages
2. **No `NotImplementedError` in Statements** -- Python marker for the universal rule (see `tdd-rules.md`: Statements must be fully functional in RED)
3. **Prefer dataclass equality** -- replace 2+ sequential per-field `assert` calls with `assert actual == expected` (frozen dataclasses do deep structural comparison by default)
4. **`await` every usecase/fake call** -- usecases and their async ports (repository, job queue, LLM client) are all `async def`; a missing `await` in a Statements method silently returns a coroutine object instead of the result, and assertions against it pass or fail for the wrong reason

## Anti-Pattern Examples

### BAD: Infrastructure leaking into test class
```python
# Test class calls mocks, clients, or adapters directly
anthropic_client_fake.stub_response("Generated text")
response = await application_client.request_generation(request, login_response)
anthropic_client_fake.verify_prompt_sent()
# GOOD: hide behind Statements -- test reads like business DSL
response = await generation_statements.request_generation(login_response)
await generation_statements.verify_prompt_sent()
```

### BAD: Setup step visible in test DSL
```python
generation = await setup_statements.create_pending_generation()
await setup_statements.attach_document_type(generation, "доклад")  # infrastructure leak!
await setup_statements.execute_action()
# GOOD: merge setup into compound given-phase method
generation = await setup_statements.given_pending_generation_for("доклад")
await setup_statements.execute_action()
```

### BAD: Scope builder/factory in test class
```python
request = CreateGenerationRequestScope.from_login(login_response.user_id).to_request()
generation_response = await create_generation.execute(request)
generation_statements.given_generations_exist_in_storage(request)
# ...
generation_statements.assert_details(
    details,
    GenerationExpectedScope.expected_details(generation_response, login_response, request)
)
# GOOD: hide scope construction behind Statements
generation_response = await generation_statements.given_generation_created(login_response)
await generation_statements.given_generations_exist_in_storage()
# ...
generation_statements.assert_details(details, generation_response, login_response)
```

### BAD: Private function or inner class in test class
```python
class TestGenerationValidation:
    async def _given_pending_generation(self):  # belongs in Statements
        login = await user_statements.given_registered_user()
        generation_id = await generation_statements.create_generation(login)
        return login, generation_id

    async def test_should_fail_when_document_type_is_invalid(self):
        login, generation_id = await self._given_pending_generation()
        # ...
# GOOD: move to Statements -- test class has zero private members
class TestGenerationValidation:
    async def test_should_fail_when_document_type_is_invalid(self):
        setup = await generation_statements.given_pending_generation()
        # ...
```

### BAD: Direct usecase call in test class
```python
generation_response = await create_generation.execute(request)  # usecase leak!
# GOOD: Statements wraps the usecase call
generation_response = await generation_statements.given_generation_created(login_response)
```

### BAD: Any assertion in test class
```python
async def test_should_reject_when_generation_not_found(self):
    login = await login_statements.login()
    await setup_statements.given_unauthorized_user(login)
    with pytest.raises(NotFoundException):
        await status_statements.get_status(login.user_id, "gen-unknown")
# GOOD: all assertions in Statements
async def test_should_reject_when_generation_not_found(self):
    login = await login_statements.login()
    await setup_statements.given_unauthorized_user(login)
    await status_statements.assert_rejects_not_found(login.user_id, "gen-unknown")
```

### BAD: Action + assertion combined in one Statements method
```python
async def assert_generation_not_found(self, login):
    with pytest.raises(GenerationNotFoundException, match="Generation not found"):
        await self.get_status.execute(self._build_request(login))
# GOOD: split into action + assertion
async def request_status_for_unknown_generation(self, login):
    try:
        await self.get_status.execute(self._build_request(login))
    except Exception as e:
        self.thrown_exception = e

def assert_generation_not_found(self):
    assert isinstance(self.thrown_exception, GenerationNotFoundException)
    assert str(self.thrown_exception) == "Generation not found"
```

### BAD: Storage port injected in Statements
```python
# BAD: verify through storage
async def assert_generation_recorded(self, generation_id, expected_status):
    generations = await self.generation_storage.find_by_id(generation_id)
    assert len(generations) == 1
    assert generations[0].status == expected_status
# GOOD: verify through usecase
async def assert_generation_recorded(self, generation_id, expected_status):
    generations = await self.get_generation_history.execute(generation_id)
    assert len(generations) == 1
    assert generations[0].status == expected_status
```

### BAD: Storage port injected in Statements (for setup)
```python
# BAD: writes to storage directly
async def given_generation_recorded(self, generation_id, status):
    await self.generation_storage.save(Generation(id=generation_id, status=status, created_at=clock.now()))
# GOOD: setup through usecase
async def given_generation_recorded(self, generation_id, status):
    await self.record_generation.execute(RecordGenerationRequest(id=generation_id, status=status))
```

### BAD: Duplicating assertion logic from another Statements class
```python
# BAD: duplicates assertions from GetGenerationStatusStatements
async def assert_generation_in_progress(self, user_id):
    status = await self.get_generation_status.get_status(user_id)
    assert status.status == "in_progress"
    assert status.document_type == self.document_type
# GOOD: inject existing Statements, delegate
async def assert_generation_in_progress(self, user_id, generation_id):
    response = await self.get_generation_status.get_status(user_id)
    self.get_generation_status_statements.assert_in_progress(response, generation_id)
    self._assert_no_document_yet(response)  # only scenario-specific
```

### BAD: Cross-Statements data passing in test class
```python
login_response = await auth_statements.login(auth_statements.login_request())
await auth_statements.assert_session_created(login_response)
await generation_statements.request_generation(
    await generation_statements.build_request_for(
        user_statements.register_request()))
# GOOD: compound methods hide all coordination
await auth_statements.assert_test_user_can_login()
await generation_statements.request_generation_for_test_user()
```

### BAD: Decomposed call when compound method exists
```python
await auth_statements.login(auth_statements.login_request())
# GOOD: use existing compound
await auth_statements.login_test_user()
```

### BAD: Unreferenced domain classes/fields from RED phase
```python
# RED created Generation (4 fields) and Document has generation: Generation
# but the test only checks a pending generation by document_type
@dataclass(frozen=True)
class Document:
    document_type: str
    generation: Generation  # no test references generation -> remove

@dataclass(frozen=True)
class Generation:  # no test references Generation at all -> delete class
    id: str
    status: str
    created_at: datetime
    prompt: str
# GOOD: Document only has the field the test actually uses
@dataclass(frozen=True)
class Document:
    document_type: str  # test asserts Document.pending("доклад") -> needs document_type only
# Generation does not exist yet -- created when a test needs it
```

## Correct Patterns

### GOOD: Dataclass Equality (recursive comparison)
```python
# Replace 2+ per-field assertions with dataclass equality
assert actual == expected  # frozen dataclasses compare all fields recursively
```
