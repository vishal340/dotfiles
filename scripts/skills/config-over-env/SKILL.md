---
name: config-over-env
description: Prefers typed config files in a project config/ directory over proliferating environment variables. Use when adding settings, feature flags, defaults, URLs, timeouts, or any configurable values.
---

# Config Over Environment Variables

## Rules

- Do not introduce new environment variables unless the value is truly environment-specific (secrets, deployment target, runtime host) or the project already mandates env-only config.
- Put configurable values in a `config/` directory, grouped by domain (e.g. `config/database.yaml`, `config/api.toml`, `config/features.json`).
- Keep config localized — colocate settings with the feature or module they serve rather than one giant global file.
- Load config from a single entry point per area (e.g. `config.load("database")`) so callers do not scatter path logic.
- Match the repo's existing config format (YAML/TOML/JSON/Python module); if none exists, default to YAML under `config/`.

## Acceptable environment variables

- Secrets (`API_KEY`, database passwords)
- Runtime environment identifiers (`NODE_ENV`, `APP_ENV`)
- Infrastructure endpoints injected at deploy time

## Examples

| Avoid | Prefer |
|-------|--------|
| `API_TIMEOUT_MS`, `API_RETRY_COUNT`, `API_BASE_URL` env vars | `config/api.yaml` with nested keys |
| Many scattered `process.env.*` reads | One loader + typed config object |
| Global `.env` for non-secret app defaults | `config/` for defaults; `.env` only for secrets/overrides |

```yaml
# config/api.yaml
api:
  base_url: https://api.example.com
  timeout_ms: 5000
  retry_count: 3
```
