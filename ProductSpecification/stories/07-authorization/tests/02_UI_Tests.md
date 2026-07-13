# Authorization — UI Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with page display (no API needed), then interaction, then form submission with
> loading state, then validation feedback, then server response handling, then
> navigation.

No prerequisite-guard section applies (no parent-resource dependency).

---

## 1. Page Display

### 1.1 Registration form displays email, password, confirm password fields

```gherkin
Given the user opens the registration page
Then the email, password, and confirm password fields are visible
And the submit button is visible
```

### 1.2 Login form displays email and password fields

```gherkin
Given the user opens the login page
Then the email and password fields are visible
And the submit button is visible
```

### 1.3 Verification-code screen displays a 6-digit input and resend action

```gherkin
Given the user has just registered and is on the verification-code screen
Then six single-digit input boxes are visible
And a resend action with a countdown is visible
```

---

## 2. User Interaction

### 2.1 Password field visibility toggle

```gherkin
Given the user is on the login form with the password field masked
When the user clicks the show-password toggle
Then the password field displays its plain-text value
```

### 2.2 Verification code input advances focus per digit

```gherkin
Given the user is on the verification-code screen with the first box focused
When the user types a digit
Then focus advances to the next box automatically
```

### 2.3 In-flight submit buttons are disabled to prevent duplicate submission

```gherkin
Given the user has filled the registration form and clicked submit
When the request is still in flight
Then the submit button is disabled
And a second click does not trigger a second request
```

### 2.3a Verify, resend, and login buttons are also disabled while in flight

```gherkin
Given the user has clicked "Confirm" on the verification-code screen
When the request is still in flight
Then the confirm button is disabled and a second click does not trigger a second request

Given the user has clicked "Resend code" after the cooldown elapsed
When the request is still in flight
Then the resend button is disabled and a second click does not trigger a second request

Given the user has clicked "Log in" on the login form
When the request is still in flight
Then the login button is disabled and a second click does not trigger a second request
```

---

## 3. Form Submission

### 3.1 Registration submission shows a loading state

```gherkin
Given the user has filled the registration form with valid data
When the user submits the form
Then a loading indicator is shown until the response arrives
```

### 3.2 Login submission shows a loading state

```gherkin
Given the user has filled the login form with credentials
When the user submits the form
Then a loading indicator is shown until the response arrives
```

---

## 4. Validation Feedback

### 4.1 Password policy hint shown inline

```gherkin
Given the user is filling the registration password field
When the user enters a password that does not meet the policy
And the user blurs the field
Then an inline validation message describes the unmet policy rule
```

### 4.2 Password/confirm mismatch shown inline

```gherkin
Given the user has entered different values in password and confirm password
When the user blurs the confirm-password field
Then an inline validation message indicates the fields do not match
```

---

## 5. Server Response Display

### 5.1 Duplicate-email error displayed on registration

```gherkin
Given the user submits registration with an email that already has an account
When the server responds with a duplicate-email error
Then the form displays that error near the email field
```

### 5.2 Generic invalid-credentials error displayed on login

```gherkin
Given the user submits login with wrong credentials
When the server responds with an invalid-credentials error
Then the form displays a single generic error message
And the message does not indicate whether the email exists
```

### 5.3 Unverified-account error displayed on login

```gherkin
Given the user submits login for an account that is not yet verified
When the server responds with the not-verified error
Then a distinct message is shown, directing the user toward verification
```

### 5.4 Account-locked screen displayed after lockout

```gherkin
Given the user's account has just been locked out by the server
When the login response indicates lockout
Then the account-locked screen is shown with the retry countdown
```

### 5.5 Wrong-code error displayed on the verification screen

```gherkin
Given the user submits an incorrect verification code
When the server responds with a code-invalid error
Then the code boxes show an error state and a message describing the mismatch
```

### 5.6 Network/timeout error is distinguished from a validation error

```gherkin
Given the user submits any auth form
When the request fails due to a network error or timeout, not a validation response
Then a retry-capable network-error state is shown, not an indefinite spinner
And it is visually distinct from a field-level validation error
```

### 5.7 Refreshing the verification-code screen does not trigger an unwanted resend

```gherkin
Given the user is on the verification-code screen with an active code
When the user refreshes the page
Then the screen re-renders without automatically issuing a new resend request
```

### 5.8 Un-submitted registration input is confirmed or restored on navigation away

```gherkin
Given the user has partially filled the registration form and not submitted it
When the user navigates away or refreshes the page
Then either a confirm-before-leaving guard fires, or the entered field values are
    restored when the user returns — data is not silently discarded
```

---

## 6. Navigation

### 6.1 "Already have an account? Log in" navigates to the login page

```gherkin
Given the user is on the registration page
When the user clicks "Already have an account? Log in"
Then the login page loads
```

### 6.2 "Don't have an account? Register" navigates to the registration page

```gherkin
Given the user is on the login page
When the user clicks "Don't have an account? Register"
Then the registration page loads
```

### 6.3 "Resend code" link, after cooldown, re-issues a code

```gherkin
Given the user is on the verification-code screen and the cooldown has elapsed
When the user clicks "Resend code"
Then a new code request is sent
And the countdown resets
```

### 6.4 Successful verification navigates to the authenticated app shell

```gherkin
Given the user has just submitted a correct verification code
When the verification succeeds
Then the authenticated app shell loads
```

### 6.5 "Back to login" from the account-locked screen navigates to the login page

```gherkin
Given the user is on the account-locked screen
When the user clicks "Back to login"
Then the login page loads
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|---------------------------|
| `the registration page` | `/register` route |
| `the login page` | `/login` route |
| `the verification-code screen` | `/verify` route, reached after registration |
| `the account-locked screen` | Rendered on a 403 lockout response from `/api/v1/auth/login` |
| `the authenticated app shell` | Post-login landing route, access token stored |
| `submit button is disabled` | `disabled` attribute set while the request promise is pending |
