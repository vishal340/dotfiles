---
name: forward-comments
description: Writes code comments that describe what the current code does, not why a change was made or what it replaced. Use when writing, editing, or reviewing comments, docstrings, or inline documentation.
---

# Forward Comments

## Rules

- Comments explain what the code does now, not the history of edits.
- Do not document why a change was made in code comments (that belongs in commit messages or PR descriptions).
- Avoid retrospective language: "previously", "used to", "changed from", "instead of", "migrated to", "no longer", "deprecated in favor of".
- When removing old behavior, delete obsolete comments rather than annotating the removal.

## Examples

```python
# Bad — change narrative
# Switched from requests to httpx for async support

# Good — current behavior
# Fetch user profile from the auth service with a 5s timeout
```

```typescript
// Bad
// Removed legacy v1 handler; v2 only now

// Good
// Validate payload against the v2 schema before enqueueing
```

```go
// Bad
// Replaced mutex with channel because of deadlock issues

// Good
// Serialize writes to the buffer through a single goroutine
```
