# AI Prompt Kit

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A small command-line toolkit for saving, tagging, searching, and reusing AI prompts.

AI Prompt Kit is designed for people who use ChatGPT, Codex, Claude, Gemini, or other AI tools every day and want a simple local prompt library that stays under their control.

## ✨ Features

- **Save prompts** with a title, tags, and notes
- **List all** saved prompts
- **Search prompts** by keyword or tag
- **Copy a prompt** into your clipboard
- **Export** your prompt library as Markdown
- **Store everything locally** in a readable JSON file
- **Prompt variables** with `{{variable}}` syntax
- **Import from Markdown** for batch importing
- **Backup and restore** functionality
- **Usage statistics** to track prompt usage
- **Tag management** to add and remove tags

## 📦 Installation

This project uses only the Python standard library.

```bash
python -m aipromptkit --help
```

Optional editable install:

```bash
python -m pip install -e .
ai-prompt-kit --help
```

## 🚀 Quick Start

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

Use a prompt with variables:

```bash
python -m aipromptkit use 1 --vars topic=Python,language=English
```

Import from Markdown:

```bash
python -m aipromptkit import prompts.md --overwrite
```

Backup and restore:

```bash
python -m aipromptkit backup create
python -m aipromptkit backup list
python -m aipromptkit backup restore prompts_2025-05-31_10-30-45_123.json
```

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

## 📁 Data Location

By default, prompts are stored in:

```text
~/.ai-prompt-kit/prompts.json
```

You can use a custom file:

```bash
python -m aipromptkit --data ./prompts.json list
```

## 🗺️ Roadmap

- [x] Prompt variables such as `{{topic}}` and `{{tone}}`
- [x] Import from Markdown
- [x] Backup and restore
- [x] Usage statistics
- [x] Tag management
- [ ] Prompt collections
- [ ] Basic quality checks for unclear prompts
- [ ] Optional sync support

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

**Made with ❤️ by AI Prompt Kit contributors**