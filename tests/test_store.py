import tempfile
import unittest
from pathlib import Path

from aipromptkit.store import PromptStore, normalize_tags


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


if __name__ == "__main__":
    unittest.main()
