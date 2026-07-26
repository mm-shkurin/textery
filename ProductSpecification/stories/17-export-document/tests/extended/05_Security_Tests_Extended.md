> These are additional edge case tests. Implement after core tests pass.

# Export document — Security Tests (Extended)

## 1. SSRF Variants

### 1.1 Embedded resources via CSS and other tags cause no request
```gherkin
Given a document whose content references external resources via CSS url() and other tags
When it is exported to pdf
Then the renderer makes no outbound request for any of them
```

## 2. Filename Edge Cases

### 2.1 A path-traversal-shaped title cannot escape the filename
```gherkin
Given a document whose title contains path separators and traversal sequences
When it is exported
Then the filename is sanitized to a safe single name
```
