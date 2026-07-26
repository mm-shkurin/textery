# Export document — Integration Tests

End-to-end from a stored document through the real render pipeline.

## 1. Round-Trip

### 1.1 A document exports to a well-formed PDF and DOCX
```gherkin
Given a document with headings, lists, and emphasis owned by the caller
When it is exported to pdf and to docx
Then each file carries its format's signature and is openable
And the visible structure matches the document content
```

### 1.2 Multibyte content survives the render pipeline
```gherkin
Given a document whose content mixes Cyrillic, an emoji, and a combining accent
When it is exported to pdf and docx
Then the rendered files contain the multibyte content intact
```

## 2. Consistency

### 2.1 The export reflects the latest saved state end to end
```gherkin
Given a document edited and saved through the editor
When it is exported immediately after
Then the file reflects the last saved content and title
```
