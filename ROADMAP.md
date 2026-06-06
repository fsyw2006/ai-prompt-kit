# Roadmap

AI Prompt Kit is intentionally small: local-first, dependency-light, and easy to trust.

## Recently Improved

- Unicode-aware keyword search and typo-tolerant fuzzy search.
- JSON and CSV import/export alongside Markdown import/export.
- Automatic tag inference with deterministic local keyword rules.
- Prompt quality scoring with local optimization suggestions.
- Safer JSON data loading with friendly corrupted-file errors.
- Atomic saves for the main prompt data file.
- More CLI input validation and broader test coverage.

## Near-Term

- Prompt update command with version history.
- History inspection and rollback for edited prompts.
- More import formats, including plain text prompt packs.
- Richer quality checks for missing examples, unclear constraints, and vague roles.
- Optional interactive flows for adding prompts without long command arguments.
- More GitHub Actions checks, including packaging smoke tests.

## Later

- Optional semantic search using a user-selected local or API-backed embedding provider.
- Prompt collections and saved search filters.
- Optional encrypted local storage.
- Optional sync support while preserving local-first defaults.
- Shell completion scripts.

## Non-Goals

- Requiring a hosted service for core functionality.
- Making prompt storage opaque or hard to inspect.
- Adding heavyweight dependencies for small features.
