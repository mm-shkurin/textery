<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/05_Security_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Export document — Security Tests

Stack-aware scenarios for the export endpoint. Generic auth, headers, CORS, HTTPS covered
globally and omitted.

## 1. Authorization / IDOR

### 1.1 A foreign or absent document is refused indistinguishably
```gherkin
Given a document owned by another account and a document id that does not exist
When the caller exports either
Then both are refused as not found
And the two responses are byte-identical
```

## 2. Header Injection

### 2.1 A title cannot inject into the response headers
```gherkin
Given a document whose title contains carriage returns, line feeds, and quotes
When it is exported
Then those characters are stripped or encoded in the filename
And no extra response header is injected
```

## 3. SSRF

### 3.1 Embedded URLs cause no outbound request
```gherkin
Given a document whose content references internal and external URLs
When it is exported to pdf
Then the renderer makes no outbound network request
```

## 4. Fail-Closed

### 4.1 An invalid format is rejected, never defaulted
```gherkin
Given a document owned by the caller
When it is exported with an unknown format
Then the request is refused as unprocessable
And no file of any format is returned
```

## 5. Disclosure

### 5.1 Render errors leak no internal detail
```gherkin
Given seeded internal sentinels (a filesystem path, a database message, a stack frame)
When an export failure is triggered
Then no sentinel appears in the response body or the logs
And internal detail is redacted to a fixed token
```
