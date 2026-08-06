> These are additional edge case tests. Implement after core tests pass.

# Editor pages — UI Tests (Extended)

## 1. Layout Edges

### 1.1 A block taller than a page does not vanish
```gherkin
Given a document containing a single block taller than one page
When the editor lays it out
Then the block is shown across consecutive sheets
And no content is clipped at a sheet boundary
```

### 1.2 A block whose height exactly fills the remaining space stays on the page
```gherkin
Given a block whose height equals the space left on the current sheet
When the editor lays the document out
Then the block is placed on the current sheet
And no empty sheet is produced after it
```

### 1.3 Deleting content removes the trailing sheet
```gherkin
Given a document of three pages
When the user deletes enough content for it to fit on two
Then the third sheet disappears
And the page count updates accordingly
```

### 1.4 A long unbreakable word does not overflow the sheet
```gherkin
Given a paragraph containing a word longer than the content box is wide
When the editor lays the document out
Then the word stays within the sheet
```

---

## 2. Page Setup Panel Edges

### 2.1 Cancelling discards the entered values
```gherkin
Given the panel is open with modified values
When the user cancels
Then the panel closes
And the document keeps its previous geometry
And reopening the panel shows the saved values, not the discarded ones
```

### 2.2 Resetting asks before discarding a configured setup
```gherkin
Given a document with a configured header, footer and non-default geometry
When the user resets the page settings
Then they are asked to confirm before the configuration is discarded
```

### 2.3 Turning numbering off removes the folios
```gherkin
Given a document showing page numbers
When the user turns numbering off and applies
Then no sheet shows a page number
```

### 2.4 Turning off the first-page exception numbers the first page
```gherkin
Given a document with numbering on and the first-page exception enabled
When the user disables the exception and applies
Then the first sheet shows its number
```

---

## 3. Counter Edges

### 3.1 A document matching its requested volume shows no shortfall
```gherkin
Given a document whose page count equals the requested volume
When the editor displays it
Then no shortfall indicator is shown
```

### 3.2 A document longer than requested is not reported as a shortfall
```gherkin
Given a document longer than the requested volume
When the editor displays it
Then no shortfall is claimed
```

### 3.3 A manually created document shows no volume comparison
```gherkin
Given a document that was never generated and has no requested volume
When the editor displays it
Then only the page counter is shown, with nothing to compare against
```

---

## 4. Mobile

### 4.1 The page strip scrolls to the current page
```gherkin
Given a document of many pages on a narrow viewport
When the caret moves to a page beyond the visible chips
Then the strip scrolls that page's chip into view
```

### 4.2 The setup sheet does not obscure the field being edited
```gherkin
Given the page setup bottom sheet is open on a narrow viewport
When the user focuses a field near the bottom and the keyboard opens
Then the focused field stays visible
```
