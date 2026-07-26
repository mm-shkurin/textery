> These are additional edge case tests. Implement after core tests pass.

# Export document — Integration Tests (Extended)

## 1. Generated-Document Export

### 1.1 A generated-then-edited document exports faithfully
```gherkin
Given a document created from a generation and then edited and saved
When it is exported to pdf and docx
Then each file reflects the edited content
```
