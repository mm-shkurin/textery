> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Security Tests (Extended)

## 1. A token for a deleted or disabled account cannot read the feed

```gherkin
Given an access token issued to an account that no longer exists
When the caller lists projects
Then the request is refused as unauthorized
```

## 2. A refresh token presented as an access token is refused

```gherkin
Given a refresh token used as the bearer credential
When the caller lists projects
Then the request is refused as unauthorized
```

## 3. Paging parameters cannot be used to infer another account's row count

```gherkin
Given two accounts with different numbers of projects
When one caller probes pages beyond its own feed
Then every response reports only its own total
```

## 4. An idempotency key is not echoed back to a caller that did not send it

```gherkin
Given a stored retry record
When any response is returned
Then no idempotency key of any account appears in the response body
```

## 5. Error responses for refused sorts do not enumerate internal column names

```gherkin
Given a sort value that is not accepted
When the caller lists projects
Then the error names the parameter but no database column
```

## 6. Retry cannot be aimed at a document id

```gherkin
Given the id of a document owned by the caller
When the caller retries that id as a generation
Then the request is refused indistinguishably from a missing generation
```
