<!-- COPIED FILE. Source of truth: ProductSpecification/stories/16-oauth-signin/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

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
