# Test Review Patterns: Acceptance Layer (Python/FastAPI)

Python/pytest code examples for acceptance test anti-patterns. For universal rules: `.claude/templates/testing/test-review-patterns.md`

## Python-Specific Rules (Acceptance)

1. **Use descriptive assertion messages** -- add a second argument to `assert` for clear failure messages
2. **Extract validation helper classes** -- parsing logic (e.g., `SetCookie` parser) belongs in helper classes
3. **Prefer dataclass equality** -- replace 2+ sequential per-field `assert` calls with `assert actual == expected` (frozen dataclasses do deep structural comparison by default)
4. **Use timedelta for timestamp comparisons** -- assert `abs(actual - expected) < timedelta(minutes=1)`. Never truncate to minutes -- truncation causes flaky failures at minute boundaries

## Anti-Pattern Examples

### BAD: Loose String Validation
```python
assert "SESSION=" in set_cookie
assert "Max-Age=0" in set_cookie
assert '"document_type":' in response.json()
```

### BAD: Multiple `in` chains
```python
assert "SESSION=" in set_cookie
assert "Path=/" in set_cookie
assert "HttpOnly" in set_cookie
```

### BAD: startsWith/matches without verifying actual content
```python
assert response.masked_token.startswith("****")
# Does NOT verify if "****5678" matches expected "5678"

import re
assert re.match(r"\*{4}\w{4}", response.masked_token)
# Does NOT verify the real last 4 chars
```

### BAD: `is not None` when actual value should be checked
```python
assert response.status is not None
# Should verify equals "pending"

assert response.expires_at is not None
# Should verify actual date
```

### BAD: `is not None` for values capturable from setup
```python
generation_statements.given_generation_requested(DOCUMENT_TYPE)
# ...
assert entry.generation_id is not None  # LOOSE
assert entry.status is not None          # LOOSE
assert entry.created_at is not None      # LOOSE
# GOOD: capture from setup, assert exact values
generation_id = generation_statements.given_generation_requested(DOCUMENT_TYPE)
# ...
assert entry.generation_id == generation_id
assert entry.status == "pending"
from datetime import datetime, timedelta
assert datetime.fromisoformat(entry.created_at) > datetime.now() - timedelta(seconds=30)
```

### BAD: Missing field assertions
```python
def assert_generation_exists(response):
    assert response.exists is True
    assert response.document_type is not None
    assert response.created_at is not None
    # MISSING: status, requested_volume
```

### BAD: Empty collections in expected values
```python
assert response.documents == []
# Should be: assert response.documents == [EXPECTED_DOCUMENT]
```

### BAD: Timestamp assertions without actual time comparison
```python
assert response.created_at is not None
# Should verify approximately NOW

assert response.expires_at > response.created_at
# Should verify actual expected date
```

### BAD: Comparison when exact period is deterministic
```python
assert response.expires_at > datetime.now()
# Should compute exact expected expiration

assert response.expires_at > response.started_at
# Should assert the exact period: (expires - started).days == 30
```

### BAD: Truthy check instead of exact value
```python
assert response.message
# Should use assert response.message == EXPECTED_MESSAGE
```

### BAD: Range checks when exact value is deterministic
```python
assert 0 < response.days_remaining <= 7
# Should be assert response.days_remaining == 7

assert 1 <= response.retry_count <= 5
# Should be assert response.retry_count == 3
```

### BAD: `in` on collections instead of exact match
```python
assert "доклад" in response.supported_document_types
# GOOD: verify ALL supported types
assert response.supported_document_types == EXPECTED_DOCUMENT_TYPES
```

### BAD: Asserting only first item in a collection
```python
assert len(response.documents) == 3
assert response.documents[0].id == "doc-001"
# MISSING: documents[1] and documents[2] are never checked
# GOOD: assert ALL documents
assert_document(response.documents[0], "doc-001", "доклад", "READY")
assert_document(response.documents[1], "doc-002", "эссе", "PENDING")
assert_document(response.documents[2], "doc-003", "сочинение", "READY")
```

### BAD: Asserting only IDs without full object contents
```python
assert generation.id == "gen-11111"
# MISSING: document_type, status, created_at
# GOOD: assert all fields
assert generation.id == "gen-11111"
assert generation.document_type == "доклад"
assert generation.status == "completed"
assert generation.created_at == "2026-07-06T12:00:00"
```

## Correct Patterns

### GOOD: Parse-then-Assert Pattern
```python
cookie = SetCookie(headers)

assert cookie.name == "SESSION", "cookie name"
assert cookie.value == "", "session value"
assert cookie.max_age == "0", "max age"
assert cookie.path == "/", "cookie path"
assert cookie.http_only is True, "http only flag"
```

### GOOD: Timestamp Assertions with Precision
```python
from datetime import datetime, timedelta

assert abs(response.created_at - datetime.now()) < timedelta(minutes=1), "created at timestamp"
assert abs(response.expires_at - (datetime.now() + timedelta(days=30))) < timedelta(minutes=1), "expiration date"
```

### GOOD: Collection Assertions with Expected Constants
```python
EXPECTED_DOCUMENT_TYPES = ["доклад", "эссе", "сочинение", "реферат"]
assert response.supported_document_types == EXPECTED_DOCUMENT_TYPES, "supported document types"
```

### GOOD: Complete Response Validation
```python
def assert_generation_exists(response):
    assert response.exists is True, "exists flag"
    assert response.document_type == EXPECTED_DOCUMENT_TYPE, "document type"
    assert response.status == EXPECTED_STATUS, "status"
    assert response.created_at > datetime.now() - timedelta(seconds=30), "created at"
```

### GOOD: Dataclass Equality (recursive comparison)
```python
# Replace 2+ per-field assertions with dataclass equality
assert actual == expected  # frozen dataclasses compare all fields recursively
```

## Assertion Improvements (Python/pytest Syntax)

| Before (Loose) | After (Strict) |
|----------------|----------------|
| `assert "status" in json_str` | `assert parsed.status == expected` |
| `assert re.match(r".*token.*", body)` | `assert parsed.token == expected_token` |
| `assert id in response` | `assert parsed.id == id` |
| `assert header.startswith("Bearer")` | `assert auth.type == "Bearer"` |
| `assert masked.startswith("****")` | `assert masked == "****" + expected_last4` |
| `assert field is not None` | `assert field == expected_value` |
| `assert field` (truthy) | `assert field == EXPECTED_MESSAGE` |
| `assert n > 0 and n <= 7` | `assert n == 7` (if deterministic) |
| `assert item in collection` | `assert collection == EXPECTED_LIST` |
| `assert documents == []` | `assert documents == EXPECTED_DOCUMENTS` |
| `assert timestamp is not None` | Truncate to minutes, compare with `==` |
| `assert expires_at > created_at` | Compute exact period and assert |
| `mock.assert_called_once_with(..., ANY)` | `mock.assert_called_once_with(..., exact_arg)` |
| 2+ sequential `assert x.field == val` | `assert actual == expected` (dataclass eq) |
