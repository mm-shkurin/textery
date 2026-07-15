# Task 4: Applying inline code to bold text silently strips the bold mark — Progress

Type: bug

## Spec
- [x] spec

## Fix: Code mark strips other marks (excludes: '_')
- [x] root cause analysis — confirmed: Tiptap's stock `Code` mark ships with `excludes: '_'`. See spec.md for reproduction and verification.
- [~] design — needs a product decision: accept as intended behavior (Fix A) or override to let bold/italic/strike survive inside code (Fix B). See spec.md "Open question".
- [ ] steps discovery
