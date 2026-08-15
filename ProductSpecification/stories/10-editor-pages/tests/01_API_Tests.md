> **Implementation Order**: sequential TDD — ownership guards → read semantics →
> write validation → write semantics (tri-state, replace, CAS) → export applies settings.

# Editor pages — API Tests

Endpoints: `GET`/`PUT /api/v1/documents/{id}` (extended with `page_settings`),
`GET /api/v1/documents/{id}/export` (contract unchanged, behaviour extended).

## 1. Ownership Guards

### 1.1 Page settings of a non-existent document are refused
```gherkin
Given an authenticated user
When they read the page settings of a document id that does not exist
Then the request is refused as not found
```

### 1.2 Another account's page settings are refused indistinguishably
```gherkin
Given a document owned by another account
When the caller reads it, saves page settings on it, and exports it
Then every one of the three is refused as not found
And each response is byte-identical to the non-existent-document case
```

---

## 2. Read Semantics

### 2.1 A never-configured document reads as unconfigured, not as the defaults
```gherkin
Given a document whose page settings have never been set
When the caller reads it
Then the page settings are reported as absent
And the response does not carry a materialized default object
```

### 2.2 Stored page settings round-trip unchanged
```gherkin
Given a document saved with non-default page settings
When the caller reads it
Then every stored key comes back with the value it was saved with
```

### 2.3 A stored object missing a later-added key reads as that key's default
```gherkin
Given a stored page-settings object written before a key was added to the schema
When the caller reads the document
Then the missing key is reported as its default
And the keys that were stored keep their stored values
```

### 2.4 A stored object carrying an undefined key or constant is read, not rejected
```gherkin
Given a stored page-settings object carrying a key this version does not define
And a stored object whose sheet size is a constant this version does not define
When the caller reads each document
Then each read succeeds
And the undefined parts resolve to their defaults
And the rest of the object is unaffected
```

---

## 3. Write Validation

Every scenario here asserts rejection **at the boundary** — never a clamp, never a partial
application.

### 3.1 An unknown key inside page settings is rejected
```gherkin
Given a document owned by the caller
When they save page settings carrying a key the schema does not define
Then the request is refused as unprocessable
And the stored page settings are unchanged
```

### 3.2 An unknown sheet size or orientation is rejected
```gherkin
Given a document owned by the caller
When they save page settings with a sheet size that is not one of the supported ones
Or with an orientation that is neither portrait nor landscape
Then each request is refused as unprocessable
```

### 3.3 Numeric bounds are inclusive and rejected one step outside
```gherkin
Given a document owned by the caller
When they save the lowest and the highest permitted font size and line height
Then each save succeeds
When they save a font size or line height one step outside its range
Then each request is refused as unprocessable
```

### 3.4 Margins that leave no content box are rejected at the exact equality
```gherkin
Given a document owned by the caller
When they save margins whose opposing pair sums to exactly the sheet dimension
Then the request is refused as unprocessable
When they save margins one step inside that sum
Then the save succeeds
```

### 3.5 Geometry whose content box cannot hold one line is rejected
```gherkin
Given a document owned by the caller
When they save a sheet size, margins, font size and line height whose content box is
  positive but shorter than a single line
Then the request is refused as unprocessable
And no pagination is attempted
```

### 3.6 Malformed numbers are rejected
```gherkin
Given a document owned by the caller
When they save a negative margin, a non-finite number, a number too large to represent,
  or a text value where a number is required
Then each request is refused as unprocessable
```

### 3.7 An over-length header or footer is rejected, never truncated
```gherkin
Given a document owned by the caller
When they save a header text one character over the limit, counted in multibyte characters
Then the request is refused as unprocessable
And no shortened header is stored
When they save a header text of exactly the limit in multibyte characters
Then the save succeeds
```

### 3.8 A rejected request leaves the content byte-identical
```gherkin
Given a document owned by the caller with known content
When they save a valid content change together with out-of-range page settings
Then the request is refused as unprocessable
And the stored content is byte-identical to what it was before the request
```

---

## 4. Write Semantics

### 4.1 Omitted page settings leave the stored value untouched
```gherkin
Given a document with page settings already saved
When the caller saves content without mentioning page settings
Then the save succeeds
And the stored page settings are unchanged
```

### 4.2 Explicit absence resets the page settings to the default preset
```gherkin
Given a document with page settings already saved
When the caller saves page settings explicitly cleared
Then the save succeeds
And the document reads back as unconfigured
```

### 4.3 A supplied object replaces the stored one wholesale
```gherkin
Given a document whose stored page settings include a header text
When the caller saves a page-settings object that omits the header text
Then the stored header text is cleared, not preserved
```

### 4.4 Only allow-listed keys are persisted
```gherkin
Given a document owned by the caller
When they save valid page settings
Then the persisted object contains exactly the allow-listed keys
And no part of the submitted request body is stored verbatim
```

### 4.5 Header text is normalized and round-trips byte-exact
```gherkin
Given a document owned by the caller
When they save a header text containing a combining accent, an emoji and Cyrillic
Then the stored text is in normalized form
And reading it back returns bytes identical to the normalized submission
```

### 4.6 A stale version is refused on a page-settings save
```gherkin
Given two readers holding the same document version
When the first saves page settings successfully
And the second saves page settings under the version it read
Then the second is refused as a conflict
And the first writer's settings survive
```

### 4.7 Replaying an identical save applies it once
```gherkin
Given a document owned by the caller
When the identical save request is sent twice
Then the resulting content and page settings equal a single application
```

### 4.8 A content save and a settings save do not silently drop each other
```gherkin
Given a document owned by the caller
When a content save and a page-settings save are interleaved on the same document
Then each either succeeds or is refused as a conflict
And no accepted save is silently overwritten by the other
```

---

## 5. Export Applies the Settings

### 5.1 An export immediately after a settings save reflects the new geometry
```gherkin
Given a document owned by the caller
When they save new page settings
And export the document immediately afterwards
Then the exported file carries the geometry and header text just saved
```

### 5.2 Manual page breaks are honoured in both formats
```gherkin
Given a document containing a manual page break
When the caller exports it as pdf and as docx
Then in each file the content after the break starts a new page
```

### 5.3 A default-settings document exports exactly as it did before this story
```gherkin
Given a document with no page settings and no manual breaks
When the caller exports it as pdf and as docx
Then each file matches the output produced before page settings existed
```

### 5.4 A partially applicable render fails instead of dropping an element
```gherkin
Given a document whose header, geometry, manual break or numbering cannot be applied
When the caller exports it
Then the request fails with the sanctioned error
And no file is returned with that element silently omitted
```

### 5.5 An unresolvable document font fails the export rather than substituting metrics
```gherkin
Given the bundled document font cannot be resolved during a render
When the caller exports the document
Then the request fails with the sanctioned error
And no file laid out in a substitute face is returned
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `an authenticated user` | Valid access-token Bearer header |
| `reads / saves page settings` | `GET` / `PUT /api/v1/documents/{id}` with the `page_settings` object |
| `saves content without mentioning page settings` | `PUT` body omitting the `page_settings` key entirely |
| `page settings explicitly cleared` | `PUT` body with `page_settings: null` |
| `refused as unprocessable` | HTTP 422 with the generic error body |
| `refused as not found` | HTTP 404, identical body for absent and foreign |
| `refused as a conflict` | HTTP 409 from the version CAS |
| `the persisted object` | The `page_settings` JSONB column read directly from the DB |
| `normalized form` | NFC |
| `exports the document` | `GET /api/v1/documents/{id}/export?format=pdf\|docx` |
| `the sanctioned error` | HTTP 500 with the generic client-safe body, no internals |
