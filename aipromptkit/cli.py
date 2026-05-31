from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .store import DEFAULT_DATA_FILE, Prompt, PromptStore, normalize_tags, extract_variables, replace_variables


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

    use_parser = subparsers.add_parser("use", help="Use a prompt with variable substitution.")
    use_parser.add_argument("id", type=int, help="Prompt id.")
    use_parser.add_argument(
        "--vars",
        default="",
        help="Variables as key=value pairs separated by commas (e.g., topic=Python,language=English).",
    )
    use_parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy the result to clipboard.",
    )

    import_parser = subparsers.add_parser("import", help="Import prompts from Markdown file.")
    import_parser.add_argument("input", help="Input Markdown file.")
    import_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing prompts with same title.",
    )

    tag_parser = subparsers.add_parser("tag", help="Manage prompt tags.")
    tag_subparsers = tag_parser.add_subparsers(dest="tag_command", required=True)
    add_tag_parser = tag_subparsers.add_parser("add", help="Add a tag to a prompt.")
    add_tag_parser.add_argument("id", type=int, help="Prompt id.")
    add_tag_parser.add_argument("tag", help="Tag to add.")
    remove_tag_parser = tag_subparsers.add_parser("remove", help="Remove a tag from a prompt.")
    remove_tag_parser.add_argument("id", type=int, help="Prompt id.")
    remove_tag_parser.add_argument("tag", help="Tag to remove.")
    list_tags_parser = tag_subparsers.add_parser("list", help="List all tags.")

    backup_parser = subparsers.add_parser("backup", help="Manage prompt backups.")
    backup_subparsers = backup_parser.add_subparsers(dest="backup_command", required=True)
    backup_create_parser = backup_subparsers.add_parser("create", help="Create a new backup.")
    backup_list_parser = backup_subparsers.add_parser("list", help="List all backups.")
    backup_restore_parser = backup_subparsers.add_parser("restore", help="Restore from a backup.")
    backup_restore_parser.add_argument("name", help="Backup filename to restore from.")

    stats_parser = subparsers.add_parser("stats", help="View prompt usage statistics.")
    stats_parser.add_argument(
        "--most-used",
        action="store_true",
        help="Show most used prompts.",
    )
    stats_parser.add_argument(
        "--recently-used",
        action="store_true",
        help="Show recently used prompts.",
    )
    stats_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of prompts to show (default: 10).",
    )

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

        if args.command == "use":
            prompt = store.get(args.id)
            
            # Record usage
            store.record_usage(args.id)
            
            # Parse variables
            variables = {}
            if args.vars:
                for pair in args.vars.split(","):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        variables[key.strip()] = value.strip()
            
            # Replace variables
            result_text = replace_variables(prompt.body, variables)
            
            # Check for missing variables
            remaining_vars = extract_variables(result_text)
            if remaining_vars:
                print(f"Warning: Missing variables: {', '.join([v[0] for v in remaining_vars])}")
                print("You can provide them with --vars option.")
                print()
            
            # Copy to clipboard if requested
            if args.copy:
                try:
                    copy_to_clipboard(result_text)
                    print(f"Copied prompt #{prompt.id} with variables to clipboard!")
                except OSError as error:
                    print(f"Error copying to clipboard: {error}", file=sys.stderr)
            else:
                print_prompt_detail_with_text(prompt, result_text)
            
            return 0

        if args.command == "import":
            imported = store.import_from_markdown(Path(args.input).expanduser(), args.overwrite)
            if imported:
                print(f"Imported {len(imported)} prompts:")
                for prompt in imported:
                    print(f"  - {prompt.title} (#{prompt.id})")
            else:
                print("No new prompts to import.")
            return 0

        if args.command == "tag":
            if args.tag_command == "add":
                try:
                    store.add_tag(args.id, args.tag)
                    prompt = store.get(args.id)
                    print(f"Added tag '{args.tag}' to prompt #{prompt.id}: {prompt.title}")
                    return 0
                except LookupError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    return 1
            
            if args.tag_command == "remove":
                try:
                    store.remove_tag(args.id, args.tag)
                    prompt = store.get(args.id)
                    print(f"Removed tag '{args.tag}' from prompt #{prompt.id}: {prompt.title}")
                    return 0
                except LookupError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    return 1
            
            if args.tag_command == "list":
                tags = store.get_all_tags()
                if not tags:
                    print("No tags found.")
                    return 0
                
                print("Tags:")
                for tag in tags:
                    prompts = store.get_prompts_by_tag(tag)
                    print(f"  {tag}: {len(prompts)} prompt(s)")
                return 0

        if args.command == "backup":
            if args.backup_command == "create":
                backup_path = store.create_backup()
                print(f"Backup created: {backup_path.name}")
                print(f"Location: {backup_path.parent}")
                return 0
            
            if args.backup_command == "list":
                backups = store.list_backups()
                if not backups:
                    print("No backups found.")
                    return 0
                
                print(f"{'Name':<30} {'Size':<10} {'Created':<20}")
                print("-" * 60)
                for backup in backups:
                    size_kb = backup["size"] / 1024
                    print(f"{backup['name']:<30} {size_kb:<10.1f}KB {backup['created']:<20}")
                return 0
            
            if args.backup_command == "restore":
                try:
                    store.restore_backup(args.name)
                    print(f"Successfully restored from backup: {args.name}")
                    print("A new backup of the previous state was created automatically.")
                    return 0
                except FileNotFoundError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    return 1

        if args.command == "stats":
            if args.most_used:
                print_prompt_usage_table(store.get_most_used(args.limit), f"Most used prompts (top {args.limit}):")
                return 0
            
            if args.recently_used:
                print_prompt_usage_table(store.get_recently_used(args.limit), f"Recently used prompts (top {args.limit}):")
                return 0
            
            # Default: show overall stats
            stats = store.get_stats()
            print("Prompt Statistics:")
            print(f"  Total prompts: {stats['total_prompts']}")
            print(f"  Used prompts: {stats['used_prompts']}")
            print(f"  Unused prompts: {stats['unused_prompts']}")
            print(f"  Total usage: {stats['total_usage']}")
            print(f"  Average usage per prompt: {stats['average_usage']:.1f}")
            
            if stats['used_prompts'] > 0:
                print("\nTop 5 most used prompts:")
                print_prompt_usage_table(store.get_most_used(5), "")
            
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


def print_prompt_detail_with_text(prompt: Prompt, text: str) -> None:
    tags = ", ".join(prompt.tags) if prompt.tags else "-"
    print(f"#{prompt.id} {prompt.title}")
    print(f"Tags: {tags}")
    if prompt.notes:
        print(f"Notes: {prompt.notes}")
    print()
    print(text)


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


def print_prompt_usage_table(prompts: list[Prompt], header: str) -> None:
    """Print a table of prompts with usage information."""
    if header:
        print(header)
    if not prompts:
        print("No prompts found.")
        return
    print(f"{'ID':<4} {'Title':<32} {'Used':<8} {'Last Used':<20}")
    print("-" * 64)
    for prompt in prompts:
        prompt_title = truncate(prompt.title, 30)
        last_used = prompt.last_used_at[:19] if prompt.last_used_at else "Never"
        print(f"{prompt.id:<4} {prompt_title:<32} {prompt.usage_count:<8} {last_used:<20}")


if __name__ == "__main__":
    raise SystemExit(main())
