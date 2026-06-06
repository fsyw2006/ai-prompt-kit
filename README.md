# AI Prompt Kit

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI Prompt Kit is a lightweight local-first CLI for saving, tagging, searching, importing, exporting, and reusing AI prompts.

It is designed for people who use ChatGPT, Codex, Claude, Gemini, or other AI tools every day and want a readable prompt library that stays under their control.

## Features

- Save prompts with a title, body, tags, notes, starred state, and usage stats.
- Search by keyword or tag, including Unicode-aware matching and fuzzy search for typos.
- Infer lightweight automatic tags from prompt text with `--auto-tags`.
- Use prompt variables with `{{variable}}`, defaults, and built-in date/time variables.
- Import and export prompt libraries as Markdown, JSON, or CSV.
- Score prompt quality and get deterministic local optimization suggestions.
- Copy prompts to the clipboard on Windows, macOS, and Linux when clipboard tools are available.
- Create, list, and restore local backups.
- Store everything locally in a readable JSON file.

## Installation

This project uses only the Python standard library.

Run from the project root:

```bash
python -m aipromptkit --help
```

Optional editable install:

```bash
python -m pip install -e .
ai-prompt-kit --help
```

## Quick Start

Add a prompt:

```bash
python -m aipromptkit add "Code reviewer" \
  --tags coding,review \
  --body "Review this code for bugs, edge cases, and missing tests."
```

Add a prompt and infer tags automatically:

```bash
python -m aipromptkit add "Python test reviewer" \
  --body "Review Python tests and suggest missing edge cases in Markdown bullets." \
  --auto-tags
```

List prompts:

```bash
python -m aipromptkit list
python -m aipromptkit list --starred
```

Show a prompt:

```bash
python -m aipromptkit show 1
```

## Search

Search by keyword:

```bash
python -m aipromptkit search review
```

Filter by tag:

```bash
python -m aipromptkit search --tag coding
```

Use fuzzy search for small typos:

```bash
python -m aipromptkit search codng --fuzzy
```

Search is case-insensitive and normalizes common Unicode forms, which helps with full-width characters and non-English text.

## Prompt Variables

Use a prompt with variables:

```bash
python -m aipromptkit use 1 --vars topic=Python,language=English
```

Values containing commas can be quoted:

```bash
python -m aipromptkit use 1 --vars 'topic=AI,"tone=warm, clear"'
```

Supported built-in variables include `{{today}}`, `{{now}}`, `{{year}}`, `{{month}}`, `{{day}}`, `{{time}}`, `{{timestamp}}`, and custom date formats such as `{{date:%Y-%m-%d}}`.

## Import And Export

Export to Markdown, JSON, or CSV:

```bash
python -m aipromptkit export prompts.md
python -m aipromptkit export prompts.json --format json
python -m aipromptkit export prompts.csv --format csv
```

Import from Markdown, JSON, or CSV:

```bash
python -m aipromptkit import prompts.md
python -m aipromptkit import prompts.json --format json
python -m aipromptkit import prompts.csv --format csv
```

Use `--overwrite` to replace existing prompts with the same title:

```bash
python -m aipromptkit import prompts.json --format json --overwrite
```

## Quality Checks

Score one prompt and get improvement suggestions:

```bash
python -m aipromptkit quality 1
```

Score all prompts:

```bash
python -m aipromptkit quality
```

The quality score is local and deterministic. It checks for practical prompt signals such as clear task verbs, enough context, output format guidance, and tags.

## Backups

Create, list, and restore backups:

```bash
python -m aipromptkit backup create
python -m aipromptkit backup list
python -m aipromptkit backup restore prompts_2026-06-06_10-30-45_123.json
```

The tool also creates a safety backup before restoring another backup.

## Stats And Tags

View usage statistics:

```bash
python -m aipromptkit stats
python -m aipromptkit stats --most-used
python -m aipromptkit stats --recently-used
```

Manage tags:

```bash
python -m aipromptkit tag list
python -m aipromptkit tag add 1 newtag
python -m aipromptkit tag remove 1 oldtag
```

Star prompts:

```bash
python -m aipromptkit star add 1
python -m aipromptkit star list
python -m aipromptkit star remove 1
```

## Data Location

By default, prompts are stored in:

```text
~/.ai-prompt-kit/prompts.json
```

Use a custom file:

```bash
python -m aipromptkit --data ./prompts.json list
```

If the data file is invalid JSON or has an unexpected schema, AI Prompt Kit reports a friendly error and suggests restoring from backup.

## Development

Run tests:

```bash
python -m unittest discover -s tests -v
```

Run a CLI smoke test:

```bash
python -m aipromptkit --data ./sample-prompts.json add "Reviewer" --body "Review this prompt." --auto-tags
python -m aipromptkit --data ./sample-prompts.json quality
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and [ROADMAP.md](ROADMAP.md) for planned work.

## License

MIT License. See [LICENSE](LICENSE) for details.
