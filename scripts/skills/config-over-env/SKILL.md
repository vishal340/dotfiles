---
name: config-over-env
description: >-
  Prefers typed config files in a project config/ directory over proliferating
  environment variables. Use when adding settings, feature flags, defaults,
  URLs, timeouts, or any configurable values—including scripts and notebooks.
  Never uses dbutils.widgets; notebook inputs go in plain notebook text.
---

# Config Over Environment Variables

## Rules

- Do not introduce new environment variables unless the value is truly environment-specific (secrets, deployment target, runtime host) or the project already mandates env-only config.
- Put configurable values in a `config/` directory, grouped by domain (e.g. `config/database.yaml`, `config/api.toml`, `config/features.json`).
- Keep config localized — colocate settings with the feature or module they serve rather than one giant global file.
- Load config from a single entry point per area (e.g. `config.load("database")`) so callers do not scatter path logic.
- Match the repo's existing config format (YAML/TOML/JSON/Python module); if none exists, default to YAML under `config/`.
- **One config source only.** Do not offer parallel ways to set the same value (YAML *and* notebook cell *and* CLI *and* env for the same knobs).

## Scripts and notebooks

- Prefer loading from `config/` (or the project's existing single config entry point).
- **Never use `dbutils.widgets`** (no `widgets.text`, `widgets.dropdown`, `widgets.get`, etc.). Do not suggest or scaffold them.
- When a notebook needs run-specific inputs, put them as plain assignments in a parameters cell (edit the notebook text). That cell is the only input layer for those values.
- Do not also add argparse/click flags or env overrides for values already set in `config/` or the parameters cell—unless the user explicitly asks for that mechanism *and* it replaces (not duplicates) the previous one.
- Shared defaults belong in `config/`. Notebook-only knobs belong in the parameters cell—not both for the same key.

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
| `dbutils.widgets.*` for notebook inputs | Plain assignments in a notebook parameters cell |
| Parameters cell + `config/` keys for the same values | One source per knob |
| Script: argparse defaults that duplicate YAML keys | Read YAML; CLI only if user asked and it is the only override layer |

```yaml
# config/api.yaml
api:
  base_url: https://api.example.com
  timeout_ms: 5000
  retry_count: 3
```

```python
# Good — shared settings from config
cfg = load_config("pipeline")

# Good — notebook-only inputs as plain text (edit in cell)
input_table = "main.bronze.events"
lookback_days = 7

# Bad — never do this
dbutils.widgets.text("input_table", "main.bronze.events")
input_table = dbutils.widgets.get("input_table")
```
