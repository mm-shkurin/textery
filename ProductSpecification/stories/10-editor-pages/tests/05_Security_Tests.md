# Editor pages — Security Tests

Attack surface added by this story: one client-writable object (`page_settings`) persisted
as JSONB, and free user text (`header_text` / `footer_text`) rendered into three different
sinks — editor HTML, a PDF stylesheet, and DOCX header XML.

Out of scope here, tested globally: unauthenticated access, security headers, CORS, HTTPS.

---

## 1. Authorization

### 1.1 Page settings of a foreign document cannot be read, written, or exported
```gherkin
Given a document owned by another account
When the caller reads it, saves page settings on it, and exports it
Then all three are refused as not found
And no response distinguishes a foreign document from an absent one
```

---

## 2. Mass Assignment

### 2.1 Only the allow-listed page-settings keys are persisted
```gherkin
Given a document owned by the caller
When they save page settings carrying an extra key alongside valid ones
Then the request is refused
And the stored object carries no trace of the extra key
And no part of the submitted body is stored verbatim
```

### 2.2 Server-owned fields remain unwritable
```gherkin
Given a document owned by the caller
When they save page settings together with server-owned document fields
Then the server-owned fields are unchanged
And ownership cannot be altered through this request
```

---

## 3. Injection Into Render Sinks

### 3.1 Header text carrying markup cannot execute in the editor
```gherkin
Given a document whose header text contains a script tag, an event handler attribute
  and a javascript-scheme link
When the editor displays the document
Then the header renders as literal text
And no script executes
```

### 3.2 Header text cannot break out of the DOCX header XML
```gherkin
Given a document whose header text contains angle brackets, quotes, an ampersand
  and control characters
When the document is exported as docx
Then the resulting file is well-formed
And the header renders as the literal submitted text
```

### 3.3 The page-number placeholder syntax in user text is not interpreted
```gherkin
Given a document whose header text contains the page-number placeholder syntax
When the document is displayed and exported
Then the text appears literally
And it is not substituted with a page number
```

### 3.4 Geometry values cannot inject into the generated stylesheet
```gherkin
Given a document owned by the caller
When they save a geometry value carrying stylesheet metacharacters or a unit suffix
Then the request is refused at the boundary
And no such value reaches the rendered stylesheet
And the numbers in the stylesheet are emitted from validated numeric values, not
  from request text
```

---

## 4. Disclosure

### 4.1 Page-settings rejections expose no internals
```gherkin
Given a document owned by the caller
When they save page settings that are rejected for each distinct reason
Then every response body uses the generic error shape
And none contains a stack frame, an internal class or field path, a database message,
  or a filesystem path
```

### 4.2 Header and footer text does not leak into unsanitized sinks
```gherkin
Given a document whose header text contains a sentinel value
When a page-settings rejection is logged and an error is returned
Then the sentinel does not appear unescaped in the log line
```

### 4.3 DOCX metadata stays redacted after the headers extension
```gherkin
Given a document owned by an account carrying a sentinel identity value
When the document is exported as docx with headers and footers set
Then the sentinel appears in neither the document metadata nor the header XML
And the author identity remains the neutral product constant
```

---

## 5. Resource Abuse

### 5.1 Geometry that would paginate without end is refused
```gherkin
Given a document owned by the caller
When they save a geometry whose content box cannot hold a single line
Then the request is refused at the boundary
And no render or layout is attempted
```

### 5.2 Structure beyond the declared limits is refused
```gherkin
Given a document owned by the caller
When they save content exceeding the block-count or nesting-depth limit
Then the request is refused at the boundary
And the response does not depend on how long the document took to reject
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `refused as not found` | HTTP 404, identical body for absent and foreign |
| `refused at the boundary` | HTTP 422 before any render, layout or persist |
| `the generic error shape` | `{error_code, message}` with a sanctioned message |
| `the page-number placeholder syntax` | Whatever token the header/footer template uses for the page number |
| `a sentinel identity value` | A unique string seeded into the owner's profile |
| `the neutral product constant` | The fixed author value already asserted by story 17 |
| `well-formed` | The exported DOCX parses as valid OOXML |
