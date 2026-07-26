> **Implementation Order**: sequential TDD — control display → in-flight lock → states →
> stale-guard → download.

# Export document — UI Tests

Selenium against the real stack. Headless Chrome download dir configured; assert the file
lands, not the render.

## 1. Control Display

### 1.1 The editor offers a PDF and a DOCX export choice
```gherkin
Given a document open in the editor
When the user opens the export control
Then a PDF choice and a DOCX choice are shown
```

## 2. In-Flight Safety

### 2.1 The export control is disabled while a request is in flight
```gherkin
Given a document open in the editor
When the user triggers export and clicks again before it returns
Then only one export request is sent
```

## 3. States

### 3.1 An in-flight export shows a progress state
```gherkin
Given the user has triggered an export
When the file is still being generated
Then an exporting indicator is shown
```

### 3.2 An export error is shown with retry, document unchanged
```gherkin
Given the user has triggered an export
When the request fails
Then an inline error with a retry is shown
And the document view is unchanged
```

## 4. Stale-While-Dirty Guard

### 4.1 Exporting with unsaved edits saves or warns first
```gherkin
Given a document with unsaved edits open in the editor
When the user triggers an export
Then the edits are saved first, or the user is warned the export would be stale
```

## 5. Download

### 5.1 A successful export delivers a downloaded file
```gherkin
Given a document open in the editor
When the user exports it as pdf
Then a file is downloaded to the browser
```
