# Test Review Patterns: Other Layers (Python/FastAPI)

Python/pytest code examples for selenium, email, scheduling, and security test anti-patterns. For universal rules: `.claude/templates/testing/test-review-patterns.md`

## Selenium Anti-Pattern Examples

### BAD: `is not None` / truthy in Selenium when test controls data
```python
# BAD:
assert status_badge.text, "generation status"
# GOOD: capture from API setup, assert exact value
generation = generation_statements.get_generation(api_session)
expected_status = generation.status.value
assert status_badge.text == expected_status, "generation status"
```

### BAD: In-app URL navigation in Selenium tests
```python
# BAD: navigates directly via URL
def navigate_to_generation_wizard(self, app_url):
    self.driver.get(f"{app_url}/generate")
# GOOD: navigate through UI clicks
def navigate_to_generation_wizard(self, app_url):
    self.driver.get(app_url)  # app root only
    self.driver.find_element(By.CSS_SELECTOR, '[data-testid="new-generation-button"]').click()
```

### BAD: NotImplementedError in Statements
```python
# BAD: stubbed like production adapter
def assert_error_banner_displayed(self):
    raise NotImplementedError()
# GOOD: write real implementation in RED
def assert_error_banner_displayed(self):
    banner = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="error-banner"]')
    assert banner.is_displayed(), "error banner is displayed"
    assert "Something went wrong" in banner.text, "error banner contains message"
```

### BAD: Selenium assertion shallower than spec
```python
# BAD: only checks count
def assert_document_cards_displayed(self):
    cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="document-card"]')
    assert len(cards) >= 1, "document cards are displayed"
# GOOD: verify sub-elements inside each card
def assert_document_cards_displayed(self):
    cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="document-card"]')
    assert len(cards) >= 1, "document cards are displayed"
    for card in cards:
        title = card.find_element(By.CSS_SELECTOR, '[data-testid="document-title"]')
        assert title.is_displayed(), "card contains title"
        assert title.text, "title is not empty"
        status = card.find_element(By.CSS_SELECTOR, '[data-testid="document-status"]')
        assert status.is_displayed(), "card contains status badge"
        doc_type = card.find_element(By.CSS_SELECTOR, '[data-testid="document-type"]')
        assert doc_type.is_displayed(), "card contains document type"
```

## Scheduling (arq) Anti-Pattern Examples

### BAD: Asserting job completion with a bare sleep
```python
# BAD: fixed sleep hopes the job finished in time -- flaky under load
await asyncio.sleep(2)
assert fake_generation_repo.saved_status == "completed"
# GOOD: poll with tenacity until the condition holds or the timeout expires
@retry(stop=stop_after_delay(5), wait=wait_fixed(0.1))
def assert_eventually_completed():
    assert fake_generation_repo.saved_status == "completed"
assert_eventually_completed()
```

### BAD: Task function containing business logic
```python
# BAD: business logic leaks into the arq task function
async def generate_document_task(ctx: dict, generation_id: str) -> None:
    generation = await fetch_generation(generation_id)
    if generation.status != "pending":
        return
    text = await call_anthropic(generation.prompt)
    await save_document(generation_id, text)
# GOOD: delegate immediately to the usecase
async def generate_document_task(ctx: dict, generation_id: str) -> None:
    usecase: RunGenerationUseCase = ctx["container"].run_generation_usecase()
    await usecase.execute(RunGenerationRequest(generation_id=generation_id))
```

## Security Anti-Pattern Examples

### BAD: Real clock in JWT expiry tests
```python
# BAD: real time makes the test slow and occasionally flaky
token = jwt_service.issue(user_id, expires_in=timedelta(seconds=1))
await asyncio.sleep(1.5)
assert jwt_service.verify(token) is None
# GOOD: inject FakeClock and advance it
token = jwt_service.issue(user_id, expires_in=timedelta(days=30))
fake_clock.advance(31 * 24 * 3600)
with pytest.raises(ExpiredTokenException):
    jwt_service.verify(token)
```
