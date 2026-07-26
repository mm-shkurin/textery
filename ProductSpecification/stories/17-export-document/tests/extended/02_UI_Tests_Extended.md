> These are additional edge case tests. Implement after core tests pass.

# Export document — UI Tests (Extended)

## 1. Retry

### 1.1 A retry after an export error succeeds
```gherkin
Given an export error was shown
When the user retries and it succeeds
Then a file is downloaded
```

## 2. Format Choice

### 2.1 Both formats can be exported in one session
```gherkin
Given a document open in the editor
When the user exports as pdf and then as docx
Then both files are downloaded
```
