# AI Prompt Kit

A small command-line toolkit for saving, tagging, searching, and reusing AI prompts.

AI Prompt Kit is designed for people who use ChatGPT, Codex, Claude, Gemini, or other AI tools every day and want a simple local prompt library that stays under their control.

## Features

- Save prompts with a title, tags, and notes
- List all saved prompts
- Search prompts by keyword or tag
- Copy a prompt into your clipboard
- Export your prompt library as Markdown
- Store everything locally in a readable JSON file

## Installation

This project uses only the Python standard library.

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
python -m aipromptkit add "Code reviewer" --tags coding,review --body "Review this code for bugs, edge cases, and missing tests."
```

List prompts:

```bash
python -m aipromptkit list
```

Search prompts:

```bash
python -m aipromptkit search review
python -m aipromptkit search --tag coding
```

Show a prompt:

```bash
python -m aipromptkit show 1
```

Copy a prompt:

```bash
python -m aipromptkit copy 1
```

Export to Markdown:

```bash
python -m aipromptkit export prompts.md
```

## Data Location

By default, prompts are stored in:

```text
~/.ai-prompt-kit/prompts.json
```

You can use a custom file:

```bash
python -m aipromptkit --data ./prompts.json list
```

## Roadmap

- Prompt variables such as `{{topic}}` and `{{tone}}`
- Import from Markdown
- Prompt collections
- Basic quality checks for unclear prompts
- Optional sync support

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

MIT License. See [LICENSE](LICENSE).
