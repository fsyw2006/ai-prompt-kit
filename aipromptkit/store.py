from __future__ import annotations

import csv
import difflib
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Iterable


DEFAULT_DATA_FILE = Path.home() / ".ai-prompt-kit" / "prompts.json"
SUPPORTED_IMPORT_FORMATS = {"auto", "markdown", "json", "csv"}


class DataFileError(ValueError):
    """Raised when the prompt data file cannot be read safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_text(value: object) -> str:
    """Normalize text for case-insensitive Unicode-aware search."""
    return unicodedata.normalize("NFKC", str(value)).casefold()


def normalize_tags(tags: Iterable[str] | str | None) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        raw_tags = re.split(r"[,，|]", tags)
    else:
        raw_tags = tags

    normalized = []
    seen = set()
    for tag in raw_tags:
        value = normalize_text(tag).strip()
        if value and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


SEARCH_TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def tokenize_search_text(value: object) -> list[str]:
    return SEARCH_TOKEN_PATTERN.findall(normalize_text(value))


# Variable pattern: {{variable_name}} or {{variable_name:default_value}}
VARIABLE_PATTERN = re.compile(r"\{\{([\w.-]+)(?::([^}]*))?\}\}", re.UNICODE)

# Built-in variables that are automatically available.
BUILTIN_VARIABLES = {
    "today": lambda: datetime.now().strftime("%Y-%m-%d"),
    "now": lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "year": lambda: datetime.now().strftime("%Y"),
    "month": lambda: datetime.now().strftime("%m"),
    "day": lambda: datetime.now().strftime("%d"),
    "time": lambda: datetime.now().strftime("%H:%M:%S"),
    "timestamp": lambda: str(int(datetime.now().timestamp())),
}


AUTO_TAG_RULES: dict[str, tuple[str, ...]] = {
    "coding": (
        "code",
        "coding",
        "python",
        "javascript",
        "typescript",
        "debug",
        "bug",
        "test",
        "refactor",
        "review",
        "api",
        "cli",
        "代码",
        "测试",
        "调试",
    ),
    "writing": (
        "write",
        "writing",
        "blog",
        "article",
        "essay",
        "copy",
        "email",
        "newsletter",
        "story",
        "邮件",
        "文案",
        "写作",
    ),
    "research": (
        "research",
        "summarize",
        "summary",
        "analyze",
        "analyse",
        "paper",
        "source",
        "citation",
        "调研",
        "总结",
        "分析",
    ),
    "marketing": (
        "marketing",
        "campaign",
        "seo",
        "brand",
        "landing page",
        "advertisement",
        "广告",
        "营销",
        "品牌",
    ),
    "translation": (
        "translate",
        "translation",
        "translator",
        "localize",
        "chinese",
        "english",
        "japanese",
        "spanish",
        "翻译",
        "中文",
        "英文",
    ),
    "planning": (
        "plan",
        "roadmap",
        "schedule",
        "project",
        "milestone",
        "todo",
        "规划",
        "计划",
        "路线图",
    ),
    "data": (
        "sql",
        "csv",
        "excel",
        "spreadsheet",
        "data",
        "dataset",
        "metrics",
        "数据",
        "表格",
    ),
    "design": (
        "design",
        "ui",
        "ux",
        "layout",
        "image",
        "logo",
        "视觉",
        "设计",
    ),
}

QUALITY_ACTION_WORDS = {
    "act",
    "analyze",
    "build",
    "check",
    "compare",
    "create",
    "debug",
    "draft",
    "explain",
    "generate",
    "improve",
    "list",
    "plan",
    "review",
    "rewrite",
    "summarize",
    "translate",
    "write",
    "分析",
    "创建",
    "改进",
    "检查",
    "解释",
    "生成",
    "总结",
    "翻译",
    "写",
    "审查",
}
QUALITY_FORMAT_WORDS = {
    "bullet",
    "bullets",
    "format",
    "json",
    "markdown",
    "outline",
    "table",
    "步骤",
    "表格",
    "格式",
    "项目符号",
}
QUALITY_CONTEXT_WORDS = {
    "audience",
    "background",
    "constraints",
    "context",
    "examples",
    "goal",
    "requirements",
    "role",
    "tone",
    "上下文",
    "背景",
    "目标",
    "受众",
    "约束",
    "语气",
    "角色",
}


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return normalize_text(value).strip() in {"1", "true", "yes", "y", "on", "starred"}


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_text(path: Path, text: str) -> None:
    _ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def _write_json_atomic(path: Path, payload: dict) -> None:
    _ensure_parent(path)
    temp_path = path.with_name(f".{path.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temp_path.replace(path)


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
        now = _utc_now()
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
        if not isinstance(data, dict):
            raise TypeError("prompt entry must be a JSON object")

        last_used_at = data.get("last_used_at")
        return cls(
            id=int(data["id"]),
            title=str(data["title"]),
            body=str(data["body"]),
            tags=normalize_tags(data.get("tags", [])),
            notes=str(data.get("notes", "")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            usage_count=max(0, int(data.get("usage_count", 0))),
            last_used_at=str(last_used_at) if last_used_at else None,
            starred=_coerce_bool(data.get("starred", False)),
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


def extract_variables(text: str) -> list[tuple[str, str]]:
    """Extract variable names and defaults from text."""
    return VARIABLE_PATTERN.findall(text)


def find_missing_variables(text: str, variables: dict[str, str]) -> list[str]:
    """Return variables that need user-provided values."""
    missing = []
    seen = set()
    for name, default in extract_variables(text):
        if name in variables or name in BUILTIN_VARIABLES:
            continue
        if name == "date" and default:
            continue
        if default:
            continue
        if name not in seen:
            missing.append(name)
            seen.add(name)
    return missing


def replace_variables(text: str, variables: dict[str, str]) -> str:
    """Replace variables in text with provided values.

    Supports built-in variables: {{today}}, {{now}}, {{year}}, {{month}}, {{day}},
    {{time}}, and {{timestamp}}. Also supports custom date formats such as
    {{date:%Y-%m-%d}}.
    """

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        default_value = match.group(2) if match.group(2) is not None else ""

        if var_name in variables:
            return variables[var_name]

        if var_name in BUILTIN_VARIABLES:
            return BUILTIN_VARIABLES[var_name]()

        if var_name == "date" and default_value:
            try:
                return datetime.now().strftime(default_value)
            except ValueError:
                return default_value

        if default_value:
            return default_value
        return match.group(0)

    return VARIABLE_PATTERN.sub(replacer, text)


def infer_tags(
    title: str,
    body: str,
    notes: str = "",
    existing_tags: Iterable[str] | None = None,
    limit: int = 5,
) -> list[str]:
    """Infer lightweight local tags from prompt text using keyword rules."""
    existing = set(normalize_tags(existing_tags))
    text = normalize_text(" ".join([title, body, notes]))
    scores: dict[str, int] = {}

    for tag, keywords in AUTO_TAG_RULES.items():
        if tag in existing:
            continue
        for keyword in keywords:
            if normalize_text(keyword) in text:
                scores[tag] = scores.get(tag, 0) + 1

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [tag for tag, _ in ranked[:limit]]


def analyze_prompt_quality(title: str, body: str, tags: Iterable[str] | None = None, notes: str = "") -> dict[str, object]:
    """Score a prompt with deterministic local heuristics."""
    body = body.strip()
    normalized_tags = normalize_tags(tags)
    text = normalize_text(" ".join([title, body, notes]))
    variables = extract_variables(body)
    score = 100
    issues: list[str] = []
    suggestions: list[str] = []

    if len(body) < 40:
        score -= 30
        issues.append("Prompt body is very short.")
        suggestions.append("Add more context, constraints, and the desired output style.")
    elif len(body) < 120:
        score -= 10
        suggestions.append("Consider adding examples, constraints, or acceptance criteria.")

    if not any(word in text for word in QUALITY_ACTION_WORDS):
        score -= 15
        issues.append("Prompt does not include a clear task verb.")
        suggestions.append("Start with a concrete action such as review, write, summarize, or translate.")

    if not any(word in text for word in QUALITY_FORMAT_WORDS):
        score -= 10
        suggestions.append("Specify the expected output format, such as bullets, Markdown, JSON, or a table.")

    if not any(word in text for word in QUALITY_CONTEXT_WORDS) and not variables:
        score -= 10
        suggestions.append("Add role, audience, goal, tone, or background context.")

    if not normalized_tags:
        score -= 5
        suggested_tags = infer_tags(title, body, notes)
        if suggested_tags:
            suggestions.append(f"Add tags such as: {', '.join(suggested_tags)}.")
        else:
            suggestions.append("Add one or two tags to make the prompt easier to find.")

    if len(body) > 4000:
        score -= 5
        suggestions.append("This prompt is long; split reusable instructions into sections if possible.")

    return {
        "score": max(0, min(100, score)),
        "issues": issues,
        "suggestions": list(dict.fromkeys(suggestions)),
    }


def parse_markdown_prompts(markdown_content: str) -> list[dict]:
    """Parse markdown content into prompts.

    Supported input format:
    # Prompt Title
    Tags: tag1, tag2

    ## Body
    Prompt body text

    ## Notes
    Optional notes

    Also supports the Markdown produced by ``ai-prompt-kit export``:
    ## 1. Prompt Title
    Tags: tag1, tag2

    ```text
    Prompt body text
    ```

    Notes:
    Optional notes
    """
    prompts = []
    lines = markdown_content.split("\n")

    current_prompt: dict = {}
    current_section = None
    current_content: list[str] = []
    in_code_block = False
    pending_notes = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            if in_code_block and current_prompt and current_section is None:
                current_section = "body"
                current_content = []
            continue

        is_new_prompt = False
        title = ""
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            is_new_prompt = title.lower() != "prompt library"
        elif stripped.startswith("## ") and not in_code_block:
            heading = stripped[3:].strip()
            if heading.lower() not in {"body", "正文", "notes", "笔记"}:
                title = heading
                is_new_prompt = True

        if is_new_prompt:
            if current_prompt:
                if current_section == "body" and current_content:
                    current_prompt["body"] = "\n".join(current_content).strip()
                elif current_section == "notes" and current_content:
                    current_prompt["notes"] = "\n".join(current_content).strip()
                prompts.append(current_prompt)
                current_prompt = {}
                current_content = []

            title = re.sub(r"^\d+\.\s*", "", title)
            current_prompt["title"] = title
            current_section = None
            pending_notes = False

        elif stripped.startswith("## ") and not in_code_block:
            if current_section == "body" and current_content:
                current_prompt["body"] = "\n".join(current_content).strip()
            elif current_section == "notes" and current_content:
                current_prompt["notes"] = "\n".join(current_content).strip()

            section_name = stripped[3:].strip().lower()
            if section_name in ["body", "正文"]:
                current_section = "body"
            elif section_name in ["notes", "笔记"]:
                current_section = "notes"
            else:
                current_section = None
            current_content = []
            pending_notes = False

        elif stripped.startswith("Tags:") or stripped.startswith("标签:"):
            tags_str = stripped.split(":", 1)[1].strip()
            current_prompt["tags"] = normalize_tags(tags_str)

        elif stripped == "Notes:" or stripped == "笔记:":
            if current_section == "body" and current_content:
                current_prompt["body"] = "\n".join(current_content).strip()
            current_section = "notes"
            current_content = []
            pending_notes = True

        elif current_section and (stripped or in_code_block or pending_notes):
            if stripped or in_code_block:
                current_content.append(line)
                pending_notes = False

    if current_prompt:
        if current_section == "body" and current_content:
            current_prompt["body"] = "\n".join(current_content).strip()
        elif current_section == "notes" and current_content:
            current_prompt["notes"] = "\n".join(current_content).strip()
        prompts.append(current_prompt)

    return prompts


class PromptStore:
    def __init__(self, path: Path | str = DEFAULT_DATA_FILE) -> None:
        self.path = Path(path).expanduser()

    def load(self) -> list[Prompt]:
        if not self.path.exists():
            return []

        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as error:
            raise DataFileError(
                f"Prompt data file is not valid JSON: {self.path}. "
                "Fix the file or restore a backup with 'ai-prompt-kit backup restore <name>'."
            ) from error
        except UnicodeDecodeError as error:
            raise DataFileError(f"Prompt data file is not valid UTF-8: {self.path}.") from error

        if isinstance(data, list):
            raw_prompts = data
        elif isinstance(data, dict):
            raw_prompts = data.get("prompts", [])
        else:
            raise DataFileError("Prompt data file must contain a JSON object with a 'prompts' list.")

        if not isinstance(raw_prompts, list):
            raise DataFileError("Prompt data file field 'prompts' must be a list.")

        prompts = []
        for index, item in enumerate(raw_prompts):
            try:
                prompts.append(Prompt.from_dict(item))
            except (KeyError, TypeError, ValueError) as error:
                raise DataFileError(f"Invalid prompt entry at prompts[{index}]: {error}") from error
        return prompts

    def save(self, prompts: list[Prompt]) -> None:
        payload = {"prompts": [prompt.to_dict() for prompt in prompts]}
        _write_json_atomic(self.path, payload)

    def add(
        self,
        title: str,
        body: str,
        tags: Iterable[str],
        notes: str = "",
        auto_tags: bool = False,
    ) -> Prompt:
        if not title.strip():
            raise ValueError("Title is required.")
        if not body.strip():
            raise ValueError("Prompt body is required.")

        prompt_tags = normalize_tags(tags)
        if auto_tags:
            prompt_tags = normalize_tags([*prompt_tags, *infer_tags(title, body, notes, prompt_tags)])

        prompts = self.load()
        next_id = max((prompt.id for prompt in prompts), default=0) + 1
        prompt = Prompt.create(next_id, title, body, prompt_tags, notes)
        prompts.append(prompt)
        self.save(prompts)
        return prompt

    def get(self, prompt_id: int) -> Prompt:
        for prompt in self.load():
            if prompt.id == prompt_id:
                return prompt
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def search(self, query: str = "", tag: str = "") -> list[Prompt]:
        query_terms = tokenize_search_text(query)
        tag = normalize_text(tag).strip()
        results = []

        for prompt in self.load():
            text = normalize_text(" ".join([prompt.title, prompt.body, prompt.notes, " ".join(prompt.tags)]))
            matches_query = not query_terms or all(term in text for term in query_terms)
            matches_tag = not tag or tag in prompt.tags
            if matches_query and matches_tag:
                results.append(prompt)

        return results

    def fuzzy_search(self, query: str, tag: str = "") -> list[Prompt]:
        """Fuzzy search prompts using deterministic token similarity."""
        query_terms = tokenize_search_text(query)
        tag = normalize_text(tag).strip()

        if not query_terms:
            return self.search(query="", tag=tag)

        scored_results: list[tuple[float, Prompt]] = []
        for prompt in self.load():
            if tag and tag not in prompt.tags:
                continue

            text = normalize_text(" ".join([prompt.title, prompt.body, prompt.notes, " ".join(prompt.tags)]))
            score = self._fuzzy_score(query_terms, text)
            if score > 0:
                scored_results.append((score, prompt))

        scored_results.sort(key=lambda item: (-item[0], item[1].id))
        return [prompt for _, prompt in scored_results]

    def _fuzzy_score(self, query_terms: list[str], text: str) -> float:
        tokens = tokenize_search_text(text)
        total = 0.0

        for term in query_terms:
            if term in text:
                total += 5.0
                continue

            best_ratio = 0.0
            for token in tokens:
                if not token:
                    continue
                if term in token or token in term:
                    best_ratio = max(best_ratio, 0.9)
                else:
                    best_ratio = max(best_ratio, difflib.SequenceMatcher(None, term, token).ratio())

            threshold = 0.72 if len(term) >= 5 else 0.80
            if best_ratio < threshold:
                return 0.0
            total += best_ratio * 2.0

        return total

    def record_usage(self, prompt_id: int) -> None:
        """Record that a prompt was used."""
        prompts = self.load()
        for prompt in prompts:
            if prompt.id == prompt_id:
                prompt.usage_count += 1
                prompt.last_used_at = _utc_now()
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
        tags = normalize_tags([tag])
        if not tags:
            raise ValueError("Tag is required.")

        prompts = self.load()
        for prompt in prompts:
            if prompt.id == prompt_id:
                normalized_tag = tags[0]
                if normalized_tag not in prompt.tags:
                    prompt.tags.append(normalized_tag)
                    prompt.updated_at = _utc_now()
                    self.save(prompts)
                return
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def remove_tag(self, prompt_id: int, tag: str) -> None:
        """Remove a tag from a prompt."""
        tags = normalize_tags([tag])
        if not tags:
            raise ValueError("Tag is required.")

        prompts = self.load()
        for prompt in prompts:
            if prompt.id == prompt_id:
                normalized_tag = tags[0]
                if normalized_tag in prompt.tags:
                    prompt.tags.remove(normalized_tag)
                    prompt.updated_at = _utc_now()
                    self.save(prompts)
                return
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def get_all_tags(self) -> list[str]:
        """Get all unique tags."""
        prompts = self.load()
        tags = set()
        for prompt in prompts:
            tags.update(prompt.tags)
        return sorted(tags)

    def get_prompts_by_tag(self, tag: str) -> list[Prompt]:
        """Get all prompts with a specific tag."""
        return self.search(tag=tag)

    def star(self, prompt_id: int) -> None:
        """Mark a prompt as starred."""
        prompts = self.load()
        for prompt in prompts:
            if prompt.id == prompt_id:
                prompt.starred = True
                prompt.updated_at = _utc_now()
                self.save(prompts)
                return
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def unstar(self, prompt_id: int) -> None:
        """Remove star from a prompt."""
        prompts = self.load()
        for prompt in prompts:
            if prompt.id == prompt_id:
                prompt.starred = False
                prompt.updated_at = _utc_now()
                self.save(prompts)
                return
        raise LookupError(f"No prompt found with id {prompt_id}.")

    def get_starred(self) -> list[Prompt]:
        """Get all starred prompts."""
        prompts = self.load()
        return [p for p in prompts if p.starred]

    def export_json(self, output: Path | str) -> None:
        """Export prompts to JSON file."""
        output = Path(output).expanduser()
        data = {"prompts": [p.to_dict() for p in self.load()]}
        _write_text(output, json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def export_csv(self, output: Path | str) -> None:
        """Export prompts to CSV file."""
        output = Path(output).expanduser()
        prompts = self.load()
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "id",
                "title",
                "body",
                "tags",
                "notes",
                "starred",
                "usage_count",
                "created_at",
                "updated_at",
                "last_used_at",
            ]
        )
        for prompt in prompts:
            writer.writerow(
                [
                    prompt.id,
                    prompt.title,
                    prompt.body,
                    "|".join(prompt.tags),
                    prompt.notes,
                    prompt.starred,
                    prompt.usage_count,
                    prompt.created_at,
                    prompt.updated_at,
                    prompt.last_used_at or "",
                ]
            )
        _write_text(output, buffer.getvalue())

    def import_prompts(self, input_path: Path | str, import_format: str = "auto", overwrite: bool = False) -> list[Prompt]:
        """Import prompts from Markdown, JSON, or CSV."""
        input_path = Path(input_path).expanduser()
        if not input_path.exists():
            raise FileNotFoundError(f"Import file not found: {input_path}")

        import_format = normalize_text(import_format).strip()
        if import_format not in SUPPORTED_IMPORT_FORMATS:
            raise ValueError(f"Unsupported import format: {import_format}")
        if import_format == "auto":
            import_format = self._detect_import_format(input_path)

        content = input_path.read_text(encoding="utf-8")
        if import_format == "markdown":
            prompt_dicts = parse_markdown_prompts(content)
        elif import_format == "json":
            prompt_dicts = self._parse_json_import(content, input_path)
        elif import_format == "csv":
            prompt_dicts = self._parse_csv_import(content)
        else:
            raise ValueError(f"Unsupported import format: {import_format}")

        return self._import_prompt_dicts(prompt_dicts, overwrite)

    def import_from_markdown(self, markdown_path: Path, overwrite: bool = False) -> list[Prompt]:
        """Import prompts from a markdown file."""
        return self.import_prompts(markdown_path, "markdown", overwrite)

    def _detect_import_format(self, input_path: Path) -> str:
        suffix = input_path.suffix.lower()
        if suffix in {".md", ".markdown"}:
            return "markdown"
        if suffix == ".json":
            return "json"
        if suffix == ".csv":
            return "csv"
        raise ValueError("Cannot detect import format. Use --format markdown, json, or csv.")

    def _parse_json_import(self, content: str, input_path: Path) -> list[dict]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError(f"Import file is not valid JSON: {input_path}") from error

        if isinstance(data, dict):
            prompt_dicts = data.get("prompts", [])
        elif isinstance(data, list):
            prompt_dicts = data
        else:
            raise ValueError("JSON import must contain a list or an object with a 'prompts' list.")

        if not isinstance(prompt_dicts, list):
            raise ValueError("JSON import field 'prompts' must be a list.")
        if not all(isinstance(item, dict) for item in prompt_dicts):
            raise ValueError("JSON import prompt entries must be objects.")
        return prompt_dicts

    def _parse_csv_import(self, content: str) -> list[dict]:
        reader = csv.DictReader(StringIO(content))
        if not reader.fieldnames:
            return []

        fields = {normalize_text(field).strip(): field for field in reader.fieldnames if field}
        missing = {"title", "body"} - set(fields)
        if missing:
            missing_fields = ", ".join(sorted(missing))
            raise ValueError(f"CSV import requires these columns: {missing_fields}")

        optional_fields = ["tags", "notes", "starred", "usage_count", "created_at", "updated_at", "last_used_at"]
        prompt_dicts = []
        for row in reader:
            prompt_dict = {
                "title": row.get(fields["title"], ""),
                "body": row.get(fields["body"], ""),
            }
            for field_name in optional_fields:
                source_field = fields.get(field_name)
                if source_field:
                    prompt_dict[field_name] = row.get(source_field, "")
            prompt_dicts.append(prompt_dict)
        return prompt_dicts

    def _import_prompt_dicts(self, prompt_dicts: list[dict], overwrite: bool) -> list[Prompt]:
        imported_prompts = []
        existing_prompts = self.load()
        existing_titles = {normalize_text(prompt.title).strip() for prompt in existing_prompts}
        next_id = max((prompt.id for prompt in existing_prompts), default=0) + 1

        for prompt_dict in prompt_dicts:
            title = str(prompt_dict.get("title", "")).strip()
            body = str(prompt_dict.get("body", "")).strip()

            if not title or not body:
                continue

            title_key = normalize_text(title).strip()
            if title_key in existing_titles:
                if overwrite:
                    existing_prompts = [
                        prompt for prompt in existing_prompts if normalize_text(prompt.title).strip() != title_key
                    ]
                    existing_titles.remove(title_key)
                else:
                    continue

            prompt = self._create_imported_prompt(next_id, prompt_dict)
            imported_prompts.append(prompt)
            existing_prompts.append(prompt)
            existing_titles.add(title_key)
            next_id += 1

        if imported_prompts:
            self.save(existing_prompts)
        return imported_prompts

    def _create_imported_prompt(self, prompt_id: int, data: dict) -> Prompt:
        prompt = Prompt.create(
            prompt_id,
            str(data.get("title", "")),
            str(data.get("body", "")),
            normalize_tags(data.get("tags", [])),
            str(data.get("notes", "")),
        )
        prompt.starred = _coerce_bool(data.get("starred", False))
        try:
            prompt.usage_count = max(0, int(data.get("usage_count", 0) or 0))
        except (TypeError, ValueError):
            prompt.usage_count = 0

        for field_name in ["created_at", "updated_at"]:
            value = data.get(field_name)
            if value:
                setattr(prompt, field_name, str(value))

        last_used_at = data.get("last_used_at")
        prompt.last_used_at = str(last_used_at) if last_used_at else None
        return prompt

    def create_backup(self) -> Path:
        """Create a backup of the current prompts file."""
        if not self.path.exists():
            self.save([])

        backups_dir = self.path.parent / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S") + f"_{now.microsecond // 1000:03d}"
        backup_path = backups_dir / f"prompts_{timestamp}.json"

        shutil.copy2(self.path, backup_path)
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
            backups.append(
                {
                    "name": backup_file.name,
                    "path": backup_file,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        return backups

    def restore_backup(self, backup_name: str) -> None:
        """Restore from a backup file."""
        backups_dir = self.path.parent / "backups"
        resolved_backups_dir = backups_dir.resolve()
        backup_path = (backups_dir / backup_name).resolve()
        try:
            backup_path.relative_to(resolved_backups_dir)
        except ValueError as error:
            raise ValueError("Backup name must refer to a file in the backups directory.") from error

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")

        if self.path.exists():
            backups_dir.mkdir(parents=True, exist_ok=True)
            temp_backup = backups_dir / f"pre_restore_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
            shutil.copy2(self.path, temp_backup)

        shutil.copy2(backup_path, self.path)
