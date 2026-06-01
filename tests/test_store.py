import tempfile
import unittest
from pathlib import Path

from aipromptkit.store import (
    PromptStore,
    extract_variables,
    find_missing_variables,
    normalize_tags,
    parse_markdown_prompts,
    replace_variables,
)


class PromptStoreTests(unittest.TestCase):
    def test_normalize_tags(self):
        self.assertEqual(normalize_tags("AI, coding, ai, "), ["ai", "coding"])

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


if __name__ == "__main__":
    unittest.main()
