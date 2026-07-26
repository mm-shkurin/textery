# Generate → edit — Security Tests

Stack-aware scenarios for the conversion endpoint. Generic auth (401), headers, CORS, and
HTTPS are covered globally and omitted here.

---

## 1. Authorization / IDOR

### 1.1 A foreign generation cannot be converted, and existence is not disclosed
```gherkin
Given a generation completed by another account
When the caller requests its conversion
Then the request is refused as not found
And the response is indistinguishable from a non-existent generation
```

### 1.2 A generated document is not readable or editable by another account
```gherkin
Given a document created from a generation by one account
When another account requests it by id or attempts to save it
Then the request is refused as not found
And the response is byte-identical to a truly non-existent document
```

---

## 2. Mass Assignment

### 2.1 Server-owned fields on the conversion body cannot be set
```gherkin
Given a completed generation owned by the caller
When conversion is requested with title, id, status, version, and a foreign generation id in the body
Then none of those override the server-derived or authorized values
```

---

## 3. Output Encoding / XSS

### 3.1 Model markup and dangerous URL schemes are neutralized
```gherkin
Given a generation whose content carries a script tag, an event handler, a javascript link, and a data-uri
When it is converted
Then none of them survive into stored or rendered content
```

---

## 4. Fail-Closed

### 4.1 A sanitizer or parser failure stores nothing unsanitized
```gherkin
Given a conversion that makes the sanitizer or parser error
When it is requested
Then no document is created
And no unsanitized content is persisted
```

---

## 5. Disclosure

### 5.1 Error paths leak no internal detail
```gherkin
Given a seeded internal sentinel reachable by a failing conversion
When each failure path is triggered
Then the sentinel appears in neither the response body nor the logs
```
