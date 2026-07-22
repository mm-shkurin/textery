# OAuth sign-in — UI Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

---

## 1. Callback edge states

### 1.1 Both code and error present on the callback

```gherkin
Given the visitor lands on the OAuth callback screen with both a code and an error parameter
Then the error state is shown
And no exchange request is issued
```

### 1.2 Direct visit to the callback with no parameters

```gherkin
Given the visitor opens the OAuth callback screen with no code and no error
Then the error state is shown and the user is returned to login
```

### 1.3 Loading state announces progress accessibly

```gherkin
Given the visitor lands on the OAuth callback screen with a valid handoff code
Then the loading state is exposed to assistive technology
```

---

## 2. Button behaviour

### 2.1 Provider buttons keep the entered email untouched

```gherkin
Given a visitor typed an email into the login form
When the visitor clicks a provider button
Then the full-page navigation proceeds without a client-side validation error on the email field
```
