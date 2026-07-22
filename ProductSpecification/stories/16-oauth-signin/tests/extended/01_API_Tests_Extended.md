# OAuth sign-in — API Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

---

## 1. Exchange response evolution

### 1.1 An unknown extra field in the exchange response is ignored

```gherkin
Given an exchange response carrying an unknown extra field alongside the session
When the frontend parses it
Then the session is stored and the extra field is ignored, not rejected
```

### 1.2 A 200 exchange missing a usable token is treated as failure

```gherkin
Given an exchange returns 200 with no usable access token
Then the frontend treats it as a failed sign-in, not a success
```

---

## 2. Provider parameter

### 2.1 A provider value differing only by case is rejected

```gherkin
When the start endpoint is requested for a provider value that differs from the enum only by case
Then it is rejected rather than silently normalized
```
