> These are additional edge case tests. Implement after core tests pass.

# Authorization — Security Tests (Extended)

## 1. Timing consistency between "unknown email" and "wrong password" login responses

```gherkin
Given a login attempt for a non-existent email and a login attempt for an existing
    email with the wrong password
When both requests are timed
Then response times are close enough that timing alone does not reveal account
    existence
```

## 2. XSS via email field reflected in any client-rendered error message

```gherkin
Given a registration or login request whose email field contains an HTML/script payload
When the server error response echoes the email back
Then the frontend renders it as inert text, never executes it
```
