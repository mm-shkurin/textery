> These are additional edge case tests. Implement after core tests pass.

# Authorization — UI Tests (Extended)

## 1. Password strength indicator updates as the user types

```gherkin
Given the user is typing into the registration password field
When each character is entered
Then a strength indicator updates to reflect the current policy compliance
```

## 2. Verification code paste fills all six boxes at once

```gherkin
Given the user copies a 6-digit code
When the user pastes it into the first code box
Then all six boxes populate correctly
```

## 3. Countdown timer on verification screen updates every second

```gherkin
Given the user is on the verification-code screen with an active cooldown
When one second elapses
Then the displayed countdown decrements by one second
```

## 4. Account-locked countdown updates and auto-enables retry when it reaches zero

```gherkin
Given the user is on the account-locked screen
When the cooldown countdown reaches zero
Then the login form becomes available again without a manual page reload
```
