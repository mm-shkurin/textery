# OAuth sign-in — Integration Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

---

## 1. Returning user

### 1.1 A returning provider identity resolves to the existing account

```gherkin
Given a provider identity that already has an account from a prior sign-in
When a new handoff code for that identity is exchanged
Then the existing account is returned and no duplicate is created
```

---

## 2. Both providers

### 2.1 The same email via two different providers stays two identities

```gherkin
Given the same email is asserted by VK and by Yandex
When each provider's handoff code is exchanged
Then each resolves per its own provider identity
And account-linking across providers is not attempted (deferred)
```
