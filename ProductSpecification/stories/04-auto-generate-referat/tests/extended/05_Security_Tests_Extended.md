# Auto-generate: реферат — Security Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

---

## 1. Output Encoding

### 1.1 Generated реферат content is served escaped

```gherkin
Given the provider stub returns a document containing markup
When the user reads the completed реферат
Then the markup is served escaped, not as live markup
```

The provider's output is untrusted input from the product's point of view — a model can
be talked into emitting a script tag by the very topic field scenario 1.1 of the main
file feeds it.

### 1.2 A delimiter-bearing topic cannot break out of its delimiters

```gherkin
Given a реферат request whose topic contains the template's own delimiter sequence
When the prompt is built
Then the topic remains enclosed as data
```

The escape-the-escaper case. Delimiting is only a boundary if the delimiter itself is
handled when it appears in the payload.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `served escaped` | Response body carries the escaped form; the editor renders text, not raw HTML |
| `the template's own delimiter sequence` | Whatever delimiter the domain template uses to fence user data |
