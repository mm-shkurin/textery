# OAuth sign-in — Security Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

---

## 1. Handoff-code hardening

### 1.1 A handoff code from a different session cannot be exchanged elsewhere

```gherkin
Given a handoff code minted for one sign-in attempt
When it is presented from an unrelated context
Then the exchange still binds only to the identity the code was minted for
```

---

## 2. Redirect hardening

### 2.1 A protocol-relative or scheme-crafted redirect target is rejected

```gherkin
Given the callback carries a protocol-relative or non-http redirect target
When the sign-in completes
Then the user is sent to the in-app default, never the crafted target
```
