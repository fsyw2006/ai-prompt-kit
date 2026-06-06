import json
import tempfile
import unittest
from pathlib import Path

from aipromptkit.store import (
    DataFileError,
    PromptStore,
    analyze_prompt_quality,
    extract_variables,
    find_missing_variables,
    infer_tags,
    normalize_tags,
    parse_markdown_prompts,
    replace_variables,
)


class PromptStoreTests(unittest.TestCase):
    def test_normalize_tags(self):
        self.assertEqual(normalize_tags("AI, coding, ai, "), ["ai", "coding"])
        self.assertEqual(normalize_tags("AI， coding|Review"), ["ai", "coding", "review"])

    def test_add_and_get_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")
            prompt = store.add("Reviewer", "Review this code.", ["coding"], "Useful for PRs")

            loaded = store.get(prompt.id)

            self.assertEqual(loaded.title, "Reviewer")
            self.assertEqual(loaded.body, "Review this code.")
            self.assertEqual(loaded.tags, ["coding"])
            self.assertEqual(loaded.notes, "Useful for PRs")

    def test_search_by_query_and_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")
            store.add("Reviewer", "Review Python code.", ["coding"], "")
            store.add("Writer", "Write a product brief.", ["writing"], "")

            results = store.search("python", "coding")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].title, "Reviewer")

    def test_search_handles_unicode_and_full_width_text(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")
            store.add("中文 Reviewer", "Review Ｐｙｔｈｏｎ code for bugs.", ["Coding"], "")

            results = store.search("python bugs", "CODING")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].title, "中文 Reviewer")

    def test_fuzzy_search_tolerates_typos(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")
            store.add("Reviewer", "Review Python coding patterns.", ["coding"], "")
            store.add("Writer", "Write a product brief.", ["writing"], "")

            results = store.fuzzy_search("codng")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].title, "Reviewer")

    def test_extract_variables(self):
        self.assertEqual(extract_variables("No variables"), [])
        self.assertEqual(extract_variables("{{topic}}"), [("topic", "")])
        self.assertEqual(extract_variables("{{topic:default}}"), [("topic", "default")])
        self.assertEqual(
            extract_variables("Write about {{topic}} in {{language:English}}"),
            [("topic", ""), ("language", "English")],
        )

    def test_replace_variables(self):
        self.assertEqual(replace_variables("No variables", {}), "No variables")
        self.assertEqual(replace_variables("{{topic}}", {"topic": "AI"}), "AI")
        self.assertEqual(replace_variables("{{topic:default}}", {}), "default")
        self.assertEqual(replace_variables("{{topic}}", {}), "{{topic}}")
        self.assertEqual(
            replace_variables("Write about {{topic}} in {{language:English}}", {"topic": "AI"}),
            "Write about AI in English",
        )
        self.assertEqual(
            replace_variables("Write about {{topic}} in {{language:English}}", {"topic": "AI", "language": "Chinese"}),
            "Write about AI in Chinese",
        )

    def test_find_missing_variables(self):
        self.assertEqual(find_missing_variables("{{topic}}", {}), ["topic"])
        self.assertEqual(find_missing_variables("{{topic}}", {"topic": "AI"}), [])
        self.assertEqual(find_missing_variables("{{topic:AI}}", {}), [])
        self.assertEqual(find_missing_variables("{{today}}", {}), [])

    def test_parse_markdown_prompts(self):
        markdown_content = """# Test Prompt
Tags: coding, review

## Body
This is the body.

## Notes
These are notes.

# Another Prompt
Tags: writing

## Body
Another body."""
        
        prompts = parse_markdown_prompts(markdown_content)
        
        self.assertEqual(len(prompts), 2)
        self.assertEqual(prompts[0]["title"], "Test Prompt")
        self.assertEqual(prompts[0]["tags"], ["coding", "review"])
        self.assertEqual(prompts[0]["body"], "This is the body.")
        self.assertEqual(prompts[0]["notes"], "These are notes.")
        
        self.assertEqual(prompts[1]["title"], "Another Prompt")
        self.assertEqual(prompts[1]["tags"], ["writing"])
        self.assertEqual(prompts[1]["body"], "Another body.")
        self.assertNotIn("notes", prompts[1])

    def test_parse_markdown_prompts_with_chinese_sections(self):
        markdown_content = """# 中文 Prompt
标签: 写作, 总结

## 正文
请总结这段内容。

## 笔记
适合中文材料。"""

        prompts = parse_markdown_prompts(markdown_content)

        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]["title"], "中文 Prompt")
        self.assertEqual(prompts[0]["tags"], ["写作", "总结"])
        self.assertEqual(prompts[0]["body"], "请总结这段内容。")
        self.assertEqual(prompts[0]["notes"], "适合中文材料。")

    def test_parse_exported_markdown_prompt(self):
        markdown_content = """# Prompt Library

## 1. Exported Prompt

Tags: coding, review

```text
Review this code.
```

Notes:
Useful for PRs
"""

        prompts = parse_markdown_prompts(markdown_content)

        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]["title"], "Exported Prompt")
        self.assertEqual(prompts[0]["tags"], ["coding", "review"])
        self.assertEqual(prompts[0]["body"], "Review this code.")
        self.assertEqual(prompts[0]["notes"], "Useful for PRs")

    def test_backup_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")
            store.add("Prompt 1", "Body 1", ["tag1"], "Note 1")
            
            # Create backup
            backup_path = store.create_backup()
            self.assertTrue(backup_path.exists())
            self.assertIn("prompts_", backup_path.name)
            
            # Modify data
            store.add("Prompt 2", "Body 2", ["tag2"], "Note 2")
            prompts_before = store.load()
            self.assertEqual(len(prompts_before), 2)
            
            # Restore backup
            store.restore_backup(backup_path.name)
            prompts_after = store.load()
            self.assertEqual(len(prompts_after), 1)
            self.assertEqual(prompts_after[0].title, "Prompt 1")

    def test_restore_backup_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")
            store.add("Prompt 1", "Body 1", ["tag1"], "Note 1")

            with self.assertRaisesRegex(ValueError, "backups directory"):
                store.restore_backup("../outside.json")

    def test_create_backup_without_existing_data_file(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")

            backup_path = store.create_backup()

            self.assertTrue(backup_path.exists())
            self.assertEqual(store.load(), [])

    def test_list_backups(self):
        import time
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")
            store.add("Prompt 1", "Body 1", ["tag1"], "Note 1")
            
            # Create multiple backups with a small delay to ensure different timestamps
            backup1 = store.create_backup()
            time.sleep(0.01)  # Small delay to ensure different timestamps
            backup2 = store.create_backup()
            
            backups = store.list_backups()
            self.assertEqual(len(backups), 2)
            
            # Check backup info structure
            self.assertIn("name", backups[0])
            self.assertIn("size", backups[0])
            self.assertIn("created", backups[0])

    def test_usage_stats(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")
            
            # Add prompts
            prompt1 = store.add("Prompt 1", "Body 1", ["tag1"], "Note 1")
            prompt2 = store.add("Prompt 2", "Body 2", ["tag2"], "Note 2")
            
            # Initially no usage
            stats = store.get_stats()
            self.assertEqual(stats["total_prompts"], 2)
            self.assertEqual(stats["used_prompts"], 0)
            self.assertEqual(stats["total_usage"], 0)
            
            # Record usage for prompt1
            store.record_usage(prompt1.id)
            
            # Check stats after one usage
            stats = store.get_stats()
            self.assertEqual(stats["used_prompts"], 1)
            self.assertEqual(stats["total_usage"], 1)
            
            # Record more usage
            store.record_usage(prompt1.id)
            store.record_usage(prompt1.id)
            
            # Check stats after more usage
            stats = store.get_stats()
            self.assertEqual(stats["total_usage"], 3)
            
            # Check most used prompts
            most_used = store.get_most_used()
            self.assertEqual(len(most_used), 2)
            self.assertEqual(most_used[0].id, prompt1.id)
            self.assertEqual(most_used[0].usage_count, 3)
            
            # Check recently used prompts
            recently_used = store.get_recently_used()
            self.assertEqual(len(recently_used), 1)  # Only prompt1 has been used
            self.assertEqual(recently_used[0].id, prompt1.id)

    def test_tag_management(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")
            
            # Add a prompt with some tags
            prompt = store.add("Test Prompt", "Body", ["tag1", "tag2"], "Note")
            
            # Get all tags
            tags = store.get_all_tags()
            self.assertEqual(len(tags), 2)
            self.assertIn("tag1", tags)
            self.assertIn("tag2", tags)
            
            # Add a new tag
            store.add_tag(prompt.id, "tag3")
            prompt = store.get(prompt.id)
            self.assertEqual(len(prompt.tags), 3)
            self.assertIn("tag3", prompt.tags)
            
            # Remove a tag
            store.remove_tag(prompt.id, "tag2")
            prompt = store.get(prompt.id)
            self.assertEqual(len(prompt.tags), 2)
            self.assertNotIn("tag2", prompt.tags)
            
            # Get prompts by tag
            prompts = store.get_prompts_by_tag("tag1")
            self.assertEqual(len(prompts), 1)
            self.assertEqual(prompts[0].id, prompt.id)

    def test_empty_tag_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")
            prompt = store.add("Test Prompt", "Body", ["tag1"], "Note")

            with self.assertRaisesRegex(ValueError, "Tag is required"):
                store.add_tag(prompt.id, " ")

    def test_invalid_data_file_json_has_friendly_error(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "prompts.json"
            data_path.write_text("{broken json", encoding="utf-8")
            store = PromptStore(data_path)

            with self.assertRaisesRegex(DataFileError, "not valid JSON"):
                store.load()

    def test_invalid_data_file_schema_has_friendly_error(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "prompts.json"
            data_path.write_text(json.dumps({"prompts": {"bad": "shape"}}), encoding="utf-8")
            store = PromptStore(data_path)

            with self.assertRaisesRegex(DataFileError, "must be a list"):
                store.load()

    def test_add_with_auto_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PromptStore(Path(directory) / "prompts.json")

            prompt = store.add("Code reviewer", "Review Python code for bugs and missing tests.", [], "", auto_tags=True)

            self.assertIn("coding", prompt.tags)

    def test_infer_tags_uses_keyword_rules(self):
        tags = infer_tags("Translate email", "Translate this English email into Chinese.")

        self.assertIn("translation", tags)
        self.assertIn("writing", tags)

    def test_analyze_prompt_quality(self):
        weak = analyze_prompt_quality("Weak", "Help.", [])
        strong = analyze_prompt_quality(
            "Code reviewer",
            (
                "Review the following Python code. Use Markdown bullets and include context, "
                "bugs, edge cases, missing tests, and concrete fixes for the developer audience."
            ),
            ["coding"],
        )

        self.assertLess(weak["score"], strong["score"])
        self.assertTrue(weak["issues"])

    def test_import_json_prompts(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "prompts.json"
            input_path.write_text(
                json.dumps(
                    {
                        "prompts": [
                            {
                                "title": "中文 Prompt",
                                "body": "请总结这段内容，并输出 Markdown 表格。",
                                "tags": ["写作"],
                                "starred": True,
                                "usage_count": 2,
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            store = PromptStore(Path(directory) / "data.json")

            imported = store.import_prompts(input_path, "json")

            self.assertEqual(len(imported), 1)
            self.assertEqual(imported[0].title, "中文 Prompt")
            self.assertEqual(imported[0].tags, ["写作"])
            self.assertTrue(imported[0].starred)
            self.assertEqual(imported[0].usage_count, 2)

    def test_export_and_import_csv_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            export_path = Path(directory) / "exports" / "prompts.csv"
            source = PromptStore(Path(directory) / "source.json")
            source.add("CSV Prompt", "Review this, then write a summary.", ["coding", "writing"], "Has comma")
            source.export_csv(export_path)

            target = PromptStore(Path(directory) / "target.json")
            imported = target.import_prompts(export_path, "csv")

            self.assertEqual(len(imported), 1)
            self.assertEqual(imported[0].body, "Review this, then write a summary.")
            self.assertEqual(imported[0].tags, ["coding", "writing"])

    def test_import_overwrite_matches_titles_case_insensitively(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "prompts.json"
            input_path.write_text(
                json.dumps({"prompts": [{"title": "reviewer", "body": "New body", "tags": ["new"]}]}),
                encoding="utf-8",
            )
            store = PromptStore(Path(directory) / "data.json")
            store.add("Reviewer", "Old body", ["old"], "")

            imported = store.import_prompts(input_path, "json", overwrite=True)
            prompts = store.load()

            self.assertEqual(len(imported), 1)
            self.assertEqual(len(prompts), 1)
            self.assertEqual(prompts[0].body, "New body")
            self.assertEqual(prompts[0].tags, ["new"])


if __name__ == "__main__":
    unittest.main()
