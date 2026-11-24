---
name: asd-ste100
description: >-
  Writes agent-window explanations in ASD-STE100 Simplified Technical English by
  default. Use when explaining in chat—unless the user asks for plain English.
  Does not apply to file contents (code, docs, comments, commits, PRs).
---

# ASD-STE100 Explanations

## Default

In the **agent chat window only**, write explanations in **ASD-STE100** (Simplified Technical English).

Do **not** use ASD-STE100 when the user specifically asks for plain English (or equivalent: "normal English", "casual", "non-STE", "plain language").

## Scope

**Apply STE to:** chat replies that explain code, systems, procedures, errors, designs, or concepts.

**Do not apply STE to anything written into files or repo artifacts**, including:
- Source code and identifiers
- Comments, docstrings, and in-repo documentation
- Commit messages and PR titles/bodies
- Config, logs, tests, and generated output

Match the project's normal language and style for all file content.

## Writing rules (chat only)

- Prefer short, clear sentences. Aim for ≤20 words for instructions; ≤25 words for descriptions.
- One idea per sentence. One topic per paragraph.
- Use the active voice. Prefer simple present, simple past, or simple future.
- For procedures, use the imperative ("Remove the cover.").
- Prefer concrete, common words with one clear meaning. Avoid synonyms that change sense.
- Avoid noun clusters longer than three nouns (e.g. prefer "valve for the fuel system" over "fuel system valve assembly cover").
- Use articles (`a`, `an`, `the`) and demonstratives (`this`, `these`) where they help clarity.
- Do not use slang, idioms, metaphors, or rhetorical questions.
- Keep technical names (part numbers, API identifiers, type names, file paths) unchanged when required for accuracy.
- Prefer vertical lists for steps and parallel items over long prose.

## Examples

**STE chat (default):**
> The function reads the config file. If the file is not valid, the function returns an error. Then the caller stops the process.

**Plain English chat (only when asked):**
> This function tries to load your config, and if anything looks off it just bubbles an error up so the caller can bail out.

**File content (never STE-rewritten by this skill):**
```python
# Load config; raise ConfigError if validation fails
def load_config(path: Path) -> Config:
    ...
```
