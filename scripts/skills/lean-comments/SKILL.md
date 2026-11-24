---
name: lean-comments
description: >-
  Keeps code comments sparse and to the point. Skips comments on small or
  obvious functions. Use when writing, editing, or reviewing code, comments,
  or docstrings.
---

# Lean Comments

## Rules

- Prefer clear names and structure over comments. If the code already says it, omit the comment.
- Do **not** add comments or docstrings to small, obvious functions (short helpers, getters, one-liners, thin wrappers).
- Add a comment only when the code alone is not enough: non-obvious intent, invariants, edge cases, or external constraints.
- Keep comments short and to the point. One line when possible. No restating the next line of code.
- Do not narrate control flow (`// increment i`, `// return result`, `// loop over items`).
- When editing existing code, remove redundant comments rather than leaving or expanding them.
- For comment *content* (current behavior, not change history), follow `forward-comments`.

## Examples

```python
# Bad — comment on a small obvious function
def clamp(n: float, lo: float, hi: float) -> float:
    """Clamp n to the inclusive range [lo, hi]."""
    return max(lo, min(hi, n))

# Good — no comment; name and body are enough
def clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))
```

```typescript
// Bad — narrates the code
// Check if user is admin
if (user.role === "admin") {

// Good — no comment, or only if policy is non-obvious
// Billing admins are excluded from this path (see policy §4.2)
if (user.role === "admin" && !user.billingOnly) {
```

```go
// Bad — restates the signature
// Open opens the file at path
func Open(path string) (*File, error)

// Good — comment only for a real constraint
// Open truncates an existing file; callers that need append must use Append.
func Open(path string) (*File, error)
```
