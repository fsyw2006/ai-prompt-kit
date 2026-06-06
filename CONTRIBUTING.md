# Contributing

Thanks for helping improve AI Prompt Kit.

AI Prompt Kit aims to stay lightweight, local-first, dependency-free, and friendly across Windows, macOS, and Linux.

## Good First Contributions

- Improve README examples.
- Add focused CLI tests.
- Improve error messages.
- Add import/export edge cases.
- Expand automatic tag keyword rules.
- Add prompt quality heuristics.
- Improve documentation for common workflows.

## Development Setup

Run the CLI from the project root:

```bash
python -m aipromptkit --help
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Install locally in editable mode:

```bash
python -m pip install -e .
ai-prompt-kit --help
```

## Code Guidelines

- Prefer the Python standard library unless a dependency clearly earns its weight.
- Use `pathlib.Path` for filesystem work.
- Keep CLI behavior predictable and return friendly errors for invalid input.
- Preserve Unicode text and write JSON with `ensure_ascii=False`.
- Keep storage changes backward compatible whenever possible.
- Add tests for every user-facing feature or bug fix.
- Avoid changing unrelated files in the same pull request.

## Data Safety

Prompt data is user-owned local data. Changes that read, write, import, export, restore, or migrate data should:

- Validate file shape before mutating existing data.
- Avoid silent data loss.
- Use backups or atomic writes when practical.
- Handle corrupted JSON with clear recovery guidance.
- Include tests for malformed input.

## Pull Request Guidelines

Please include:

- A short summary of the change.
- Tests that cover new behavior.
- Documentation updates for new commands or changed output.
- Notes about backward compatibility if storage behavior changes.

Before opening a PR, run:

```bash
python -m unittest discover -s tests -v
python -m aipromptkit --help
```
