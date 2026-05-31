from __future__ import annotations

import csv
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Iterable


DEFAULT_DATA_FILE = Path.home() / ".ai-prompt-kit" / "prompts.json"


@dataclass
class Prompt:
    id: int
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    usage_count: int = 0
    last_used_at: str | None = None
    starred: bool = False

    @classmethod
    def create(cls, prompt_id: int, title: str, body: str, tags: Iterable[str], notes: str) -> "Prompt":
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return cls(
            id=prompt_id,
            title=title.strip(),
            body=body.strip(),
            tags=normalize_tags(tags),
            notes=notes.strip(),
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Prompt":
        return cls(
            id=int(data["id"]),
            title=str(data["title"]),
            body=str(data["body"]),
            tags=normalize_tags(data.get("tags", [])),
            notes=str(data.get("notes", "")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            usage_count=int(data.get("usage_count", 0)),
            last_used_at=data.get("last_used_at"),
            starred=bool(data.get("starred", False)),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "tags": self.tags,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at,
            "starred": self.starred,
        }


def normalize_tags(tags: Iterable[str] | str | None) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        raw_tags = tags.split(",")
    else:
        raw_tags = tags

    normalized = []
    seen = set()
    for tag in raw_tags:
        value = str(tag).strip().lower()
        if value and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


# Variable pattern: {{variable_name}} or {{variable_name:default_value}}
VARIABLE_PATTERN = re.compile(r"\{\{(\w+)(?::([^}]*))?\}\}")

# Built-in variables that are automatically available
BUILTIN_VARIABLES = {
    "today": lambda: datetime.now().strftime("%Y-%m-%d"),
    "now": lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "year": lambda: datetime.now().strftime("%Y"),
    "month": lambda: datetime.now().strftime("%m"),
    "day": lambda: datetime.now().strftime("%d"),
    "time": lambda: datetime.now().strftime("%H:%M:%S"),
    "timestamp": lambda: str(int(datetime.now().timestamp())),
}


def extract_variables(text: str) -> list[str]:
    """Extract variable names from text."""
    return VARIABLE_PATTERN.findall(text)


def replace_variables(text: str, variables: dict[str, str]) -> str:
    """Replace variables in text with provided values.
    
    Supports built-in variables: {{today}}, {{now}}, {{year}}, {{month}}, {{day}}, {{time}}, {{timestamp}}
    Supports custom date format: {{date:YYYY-MM-DD}}
    """
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        default_value = match.group(2) if match.group(2) is not None else ""
        
        # Check if user provided a value
        if var_name in variables:
            return variables[var_name]
        
        # Check for built-in variables
        if var_name in BUILTIN_VARIABLES:
            return BUILTIN_VARIABLES[var_name]()
        
        # Check for date format variable ({{date:format}})
        if var_name == "date" and default_value:
            try:
                return datetime.now().strftime(default_value)
            except ValueError:
                return default_value
        
        # Return default value or empty string
        return default_value
    
    return VARIABLE_PATTERN.sub(replacer, text)


def parse_markdown_prompts(markdown_content: str) -> list[dict]:
    """Parse markdown content into prompts.
    
    Expected format:
    # Prompt Title
    Tags: tag1, tag2
    
    ## Body
    Prompt body text
    
    ## Notes
    Optional notes
    """
    prompts = []
    lines = markdown_content.split("\n")
    
    current_prompt = {}
    current_section = None
    current_content = []
    
    for line in lines:
        stripped = line.strip()
        
        # Check for new prompt (starts with # but not ##)
        if stripped.startswith("# ") and not stripped.startswith("## "):
            # Save previous prompt if exists
            if current_prompt:
                # Save current section content
                if current_section == "body" and current_content:
                    current_prompt["body"] = "\n".join(current_content).strip()
                elif current_section == "notes" and current_content:
                    current_prompt["notes"] = "\n".join(current_content).strip()
                prompts.append(current_prompt)
                current_prompt = {}
                current_content = []
            
            # Start new prompt
            title = stripped[2:].strip()
            # Remove any leading numbers like "1. " or "1. "
            title = re.sub(r"^\d+\.\s*", "", title)
            current_prompt["title"] = title
            current_section = None
            
        elif stripped.startswith("## "):
            # Save content of previous section
            if current_section == "body" and current_content:
                current_prompt["body"] = "\n".join(current_content).strip()
            elif current_section == "notes" and current_content:
                current_prompt["notes"] = "\n".join(current_content).strip()
            
            # Start new section
            section_name = stripped[3:].strip().lower()
            if section_name in ["body", "正文"]:
                current_section = "body"
            elif section_name in ["notes", "笔记"]:
                current_section = "notes"
            else:
                current_section = None
            current_content = []
            
        elif stripped.startswith("Tags:") or stripped.startswith("标签:"):
            # Parse tags line
            tags_str = stripped.split(":", 1)[1].strip()
            current_prompt["tags"] = normalize_tags(tags_str)
            
        elif current_section and stripped:
            # Add content to current section
            current_content.append(line)
    
    # Save last prompt
    if current_prompt:
        # Save current section content
        if current_section == "body" and current_content:
            current_prompt["body"] = "\n".join(current_content).strip()
        elif current_section == "notes" and current_content:
            current_prompt["notes"] = "\n".join(current_content).strip()
        prompts.append(current_prompt)
    
    return prompts


class PromptStore:
    def __init__(self, path: Path | str = DEFAULT_DATA_FILE) -> None:
        self.path = Path(path) if isinstance(path, str) else path

    def load(self) -> list[Prompt]:
        if not self.path.exists():
            return []

        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        prompts = data.get("prompts", [])
        return [Prompt.from_dict(item) for item in prompts]

    def save(self, prompts: list[Prompt]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"prompts": [prompt.to_dict() for prompt in prompts]}
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def add(self, title: str, body: str, tags: Iterable[str], notes: str = "") -> Prompt:
        if not title.strip():
            raise ValueError("Title is required.")
        if not body.strip():
            raise ValueError("Prompt body is required.")

        prompts = self.load()
        next_id = max((prompt.id for prompt in prompts), default=0) + 1
        prompt = Prompt.create(next_id, title, body, tags, notes)
        prompts.append(prompt)
        self.save(prompts)
        return prompt

    def get(self, prompt_id: int) -> Prompt:
        for prompt in self.load():
            if prompt.id == prompt_id:
                return prompt
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def search(self, query: str = "", tag: str = "") -> list[Prompt]:
        query = query.strip().lower()
        tag = tag.strip().lower()
        results = []

        for prompt in self.load():
            text = " ".join([prompt.title, prompt.body, prompt.notes, " ".join(prompt.tags)]).lower()
            matches_query = not query or query in text
            matches_tag = not tag or tag in prompt.tags
            if matches_query and matches_tag:
                results.append(prompt)

        return results

    def record_usage(self, prompt_id: int) -> None:
        """Record that a prompt was used."""
        prompts = self.load()
        for prompt in prompts:
            if prompt.id == prompt_id:
                prompt.usage_count += 1
                prompt.last_used_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                self.save(prompts)
                return
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def get_most_used(self, limit: int = 10) -> list[Prompt]:
        """Get the most used prompts."""
        prompts = self.load()
        return sorted(prompts, key=lambda p: p.usage_count, reverse=True)[:limit]

    def get_recently_used(self, limit: int = 10) -> list[Prompt]:
        """Get the most recently used prompts."""
        prompts = self.load()
        # Filter prompts that have been used at least once
        used_prompts = [p for p in prompts if p.last_used_at]
        return sorted(used_prompts, key=lambda p: p.last_used_at or "", reverse=True)[:limit]

    def get_stats(self) -> dict:
        """Get overall usage statistics."""
        prompts = self.load()
        total_usage = sum(p.usage_count for p in prompts)
        used_count = sum(1 for p in prompts if p.usage_count > 0)
        return {
            "total_prompts": len(prompts),
            "used_prompts": used_count,
            "unused_prompts": len(prompts) - used_count,
            "total_usage": total_usage,
            "average_usage": total_usage / len(prompts) if prompts else 0,
        }

    def add_tag(self, prompt_id: int, tag: str) -> None:
        """Add a tag to a prompt."""
        prompts = self.load()
        for prompt in prompts:
            if prompt.id == prompt_id:
                normalized_tag = tag.strip().lower()
                if normalized_tag not in prompt.tags:
                    prompt.tags.append(normalized_tag)
                    self.save(prompts)
                return
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def remove_tag(self, prompt_id: int, tag: str) -> None:
        """Remove a tag from a prompt."""
        prompts = self.load()
        for prompt in prompts:
            if prompt.id == prompt_id:
                normalized_tag = tag.strip().lower()
                if normalized_tag in prompt.tags:
                    prompt.tags.remove(normalized_tag)
                    self.save(prompts)
                return
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def get_all_tags(self) -> list[str]:
        """Get all unique tags."""
        prompts = self.load()
        tags = set()
        for prompt in prompts:
            tags.update(prompt.tags)
        return sorted(list(tags))

    def get_prompts_by_tag(self, tag: str) -> list[Prompt]:
        """Get all prompts with a specific tag."""
        return self.search(tag=tag)

    def star(self, prompt_id: int) -> None:
        """Mark a prompt as starred."""
        prompts = self.load()
        for prompt in prompts:
            if prompt.id == prompt_id:
                prompt.starred = True
                prompt.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                self.save(prompts)
                return
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def unstar(self, prompt_id: int) -> None:
        """Remove star from a prompt."""
        prompts = self.load()
        for prompt in prompts:
            if prompt.id == prompt_id:
                prompt.starred = False
                prompt.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                self.save(prompts)
                return
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def get_starred(self) -> list[Prompt]:
        """Get all starred prompts."""
        prompts = self.load()
        return [p for p in prompts if p.starred]

    def fuzzy_search(self, query: str, tag: str = "") -> list[Prompt]:
        """Fuzzy search prompts - matches partial words with typos."""
        query = query.strip().lower()
        tag = tag.strip().lower()
        
        if not query:
            return self.search(query="", tag=tag)
        
        results = []
        for prompt in self.load():
            # Check tag filter first
            if tag and tag not in prompt.tags:
                continue
            
            # Build searchable text
            text = " ".join([prompt.title, prompt.body, prompt.notes, " ".join(prompt.tags)]).lower()
            
            # Fuzzy matching: check if query words match with some tolerance
            query_words = query.split()
            matches = 0
            for qword in query_words:
                # Exact match
                if qword in text:
                    matches += 1
                    continue
                # Partial match (prefix/suffix)
                for tw in text.split():
                    if qword in tw or tw in qword:
                        matches += 1
                        break
                # Levenshtein-like: check if at least 70% of chars match
                else:
                    for tw in text.split():
                        if len(tw) >= 3 and len(qword) >= 3:
                            common = sum(1 for a, b in zip(qword, tw) if a == b)
                            similarity = common / max(len(qword), len(tw))
                            if similarity >= 0.7:
                                matches += 1
                                break
            
            if matches == len(query_words):
                results.append(prompt)
        
        return results

    def export_json(self, output: Path | str) -> None:
        """Export prompts to JSON file."""
        output = Path(output) if isinstance(output, str) else output
        prompts = self.load()
        data = {"prompts": [p.to_dict() for p in prompts]}
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def export_csv(self, output: Path | str) -> None:
        """Export prompts to CSV file."""
        output = Path(output) if isinstance(output, str) else output
        prompts = self.load()
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "title", "body", "tags", "notes", "starred", "usage_count", "created_at"])
        for p in prompts:
            writer.writerow([
                p.id,
                p.title,
                p.body,
                "|".join(p.tags),
                p.notes,
                p.starred,
                p.usage_count,
                p.created_at,
            ])
        output.write_text(buffer.getvalue(), encoding="utf-8")

    def import_from_markdown(self, markdown_path: Path, overwrite: bool = False) -> list[Prompt]:
        """Import prompts from a markdown file."""
        if not markdown_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_path}")
        
        content = markdown_path.read_text(encoding="utf-8")
        prompt_dicts = parse_markdown_prompts(content)
        
        imported_prompts = []
        existing_prompts = self.load()
        existing_titles = {prompt.title.lower() for prompt in existing_prompts}
        
        next_id = max((prompt.id for prompt in existing_prompts), default=0) + 1
        
        for prompt_dict in prompt_dicts:
            title = prompt_dict.get("title", "").strip()
            body = prompt_dict.get("body", "").strip()
            tags = prompt_dict.get("tags", [])
            notes = prompt_dict.get("notes", "").strip()
            
            if not title or not body:
                continue  # Skip prompts without title or body
            
            # Check for duplicates
            if title.lower() in existing_titles:
                if overwrite:
                    # Find and remove existing prompt
                    existing_prompts = [p for p in existing_prompts if p.title.lower() != title.lower()]
                    existing_titles.remove(title.lower())
                else:
                    continue  # Skip duplicate
            
            # Create new prompt
            prompt = Prompt.create(next_id, title, body, tags, notes)
            imported_prompts.append(prompt)
            existing_prompts.append(prompt)
            existing_titles.add(title.lower())
            next_id += 1
        
        # Save all prompts
        self.save(existing_prompts)
        return imported_prompts

    def create_backup(self) -> Path:
        """Create a backup of the current prompts file."""
        if not self.path.exists():
            raise FileNotFoundError(f"Data file not found: {self.path}")
        
        # Create backups directory
        backups_dir = self.path.parent / "backups"
        backups_dir.mkdir(exist_ok=True)
        
        # Create backup filename with timestamp (including milliseconds for uniqueness)
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S") + f"_{now.microsecond // 1000:03d}"
        backup_filename = f"prompts_{timestamp}.json"
        backup_path = backups_dir / backup_filename
        
        # Copy the file
        shutil.copy2(self.path, backup_path)
        
        # Clean up old backups (keep only last 7)
        self._cleanup_backups(backups_dir)
        
        return backup_path
    
    def _cleanup_backups(self, backups_dir: Path, keep: int = 7) -> None:
        """Remove old backups, keeping only the most recent ones."""
        backup_files = sorted(backups_dir.glob("prompts_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        for backup_file in backup_files[keep:]:
            backup_file.unlink()
    
    def list_backups(self) -> list[dict]:
        """List all available backups."""
        backups_dir = self.path.parent / "backups"
        if not backups_dir.exists():
            return []
        
        backups = []
        for backup_file in sorted(backups_dir.glob("prompts_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.name,
                "path": backup_file,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        
        return backups
    
    def restore_backup(self, backup_name: str) -> None:
        """Restore from a backup file."""
        backups_dir = self.path.parent / "backups"
        backup_path = backups_dir / backup_name
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")
        
        # Create a backup of current state before restoring
        if self.path.exists():
            # Create backup in a temporary location to avoid cleanup issues
            temp_backup = backups_dir / f"pre_restore_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
            shutil.copy2(self.path, temp_backup)
        
        # Restore the backup
        shutil.copy2(backup_path, self.path)
