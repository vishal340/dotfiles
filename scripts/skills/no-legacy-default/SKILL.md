---
name: no-legacy-default
description: Replaces old behavior outright instead of keeping parallel legacy code paths. Use when refactoring, renaming APIs, swapping implementations, or migrating formats—unless the user explicitly requests legacy support.
---

# No Legacy By Default

## Rules

- When performing a change, do not keep legacy modes unless the user explicitly says `legacy true` (or equivalent clear opt-in).
- Replace old implementations; remove dead branches, dual APIs, compatibility shims, and "old vs new" feature flags.
- Do not add `useLegacy`, `fallbackToV1`, or parallel code paths "just in case" without explicit instruction.
- Update all call sites in scope; do not leave the old path wired but unused.

## When `legacy true` is requested

- Keep the legacy path behind an explicit flag or separate module.
- Document the legacy path's current behavior (per forward-comments), not the migration story.
- Prefer isolating legacy code in clearly named files (e.g. `legacy_handler.py`) rather than interleaving with new code.

## Examples

| Avoid (default) | Do instead |
|-----------------|------------|
| `if useLegacy { old() } else { new() }` | Delete `old()`, use `new()` only |
| Rename + keep alias "for compatibility" | Rename all usages; remove alias |
| New env `USE_NEW_PARSER=false` to toggle | Switch parser; remove old parser |

```python
# Bad — default refactor keeps both paths
def parse(data, use_legacy=False):
    if use_legacy:
        return parse_v1(data)
    return parse_v2(data)

# Good — replace outright
def parse(data):
    return parse_v2(data)
```
