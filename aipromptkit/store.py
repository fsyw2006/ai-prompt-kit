from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
        }


def normalize_tags(tags: Iterable[str] | str) -> list[str]:
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


class PromptStore:
    def __init__(self, path: Path = DEFAULT_DATA_FILE) -> None:
        self.path = path

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
