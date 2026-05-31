from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .store import DEFAULT_DATA_FILE, Prompt, PromptStore, normalize_tags


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-prompt-kit",
        description="Save, tag, search, and reuse AI prompts from your terminal.",
    )
    parser.add_argument(
        "--data",
        default=str(DEFAULT_DATA_FILE),
        help=f"Path to prompt data file. Default: {DEFAULT_DATA_FILE}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new prompt.")
    add_parser.add_argument("title", help="Prompt title.")
    add_parser.add_argument("--body", required=True, help="Prompt body.")
    add_parser.add_argument("--tags", default="", help="Comma-separated tags.")
    add_parser.add_argument("--notes", default="", help="Optional notes.")

    subparsers.add_parser("list", help="List saved prompts.")

    show_parser = subparsers.add_parser("show", help="Show a prompt by id.")
    show_parser.add_argument("id", type=int, help="Prompt id.")

    search_parser = subparsers.add_parser("search", help="Search prompts.")
    search_parser.add_argument("query", nargs="?", default="", help="Keyword to search.")
    search_parser.add_argument("--tag", default="", help="Filter by tag.")

    copy_parser = subparsers.add_parser("copy", help="Copy prompt body by id.")
    copy_parser.add_argument("id", type=int, help="Prompt id.")

    export_parser = subparsers.add_parser("export", help="Export prompts to Markdown.")
    export_parser.add_argument("output", help="Output Markdown file.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = PromptStore(Path(args.data).expanduser())

    try:
        if args.command == "add":
            prompt = store.add(args.title, args.body, normalize_tags(args.tags), args.notes)
            print(f"Added prompt #{prompt.id}: {prompt.title}")
            return 0

        if args.command == "list":
            print_prompt_table(store.load())
            return 0

        if args.command == "show":
            print_prompt_detail(store.get(args.id))
            return 0

        if args.command == "search":
            print_prompt_table(store.search(args.query, args.tag))
            return 0

        if args.command == "copy":
            prompt = store.get(args.id)
            copy_to_clipboard(prompt.body)
            print(f"Copied prompt #{prompt.id}: {prompt.title}")
            return 0

        if args.command == "export":
            export_markdown(store.load(), Path(args.output))
            print(f"Exported prompts to {args.output}")
            return 0

    except (ValueError, LookupError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


def print_prompt_table(prompts: list[Prompt]) -> None:
    if not prompts:
        print("No prompts found.")
        return

    print(f"{'ID':<4} {'Title':<32} Tags")
    print("-" * 70)
    for prompt in prompts:
        title = truncate(prompt.title, 30)
        tags = ", ".join(prompt.tags) if prompt.tags else "-"
        print(f"{prompt.id:<4} {title:<32} {tags}")


def print_prompt_detail(prompt: Prompt) -> None:
    tags = ", ".join(prompt.tags) if prompt.tags else "-"
    print(f"#{prompt.id} {prompt.title}")
    print(f"Tags: {tags}")
    if prompt.notes:
        print(f"Notes: {prompt.notes}")
    print()
    print(prompt.body)


def export_markdown(prompts: list[Prompt], output: Path) -> None:
    lines = ["# Prompt Library", ""]
    for prompt in prompts:
        tags = ", ".join(prompt.tags) if prompt.tags else "-"
        lines.extend(
            [
                f"## {prompt.id}. {prompt.title}",
                "",
                f"Tags: {tags}",
                "",
                "```text",
                prompt.body,
                "```",
                "",
            ]
        )
        if prompt.notes:
            lines.extend(["Notes:", "", prompt.notes, ""])

    output.write_text("\n".join(lines), encoding="utf-8")


def copy_to_clipboard(text: str) -> None:
    if shutil.which("clip"):
        subprocess.run("clip", input=text, text=True, check=True)
        return
    if shutil.which("pbcopy"):
        subprocess.run("pbcopy", input=text, text=True, check=True)
        return
    if shutil.which("xclip"):
        subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
        return
    raise OSError("No supported clipboard command found.")


def truncate(value: str, length: int) -> str:
    if len(value) <= length:
        return value
    return value[: length - 3] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
