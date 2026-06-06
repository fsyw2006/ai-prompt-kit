import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from aipromptkit.cli import main, parse_variables, positive_int
from aipromptkit.store import PromptStore


class CLITests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_parse_variables_supports_quoted_commas(self):
        variables = parse_variables('topic=AI,"tone=warm, clear",language=中文')

        self.assertEqual(
            variables,
            {
                "topic": "AI",
                "tone": "warm, clear",
                "language": "中文",
            },
        )

    def test_parse_variables_rejects_malformed_pairs(self):
        with self.assertRaisesRegex(ValueError, "key=value"):
            parse_variables("topic=AI,badpair")

    def test_positive_int_rejects_zero(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("0")

    def test_show_rejects_non_positive_id(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "prompts.json"
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as result:
                main(["--data", str(data_path), "show", "0"])

            self.assertEqual(result.exception.code, 2)
            self.assertIn("positive integer", stderr.getvalue())

    def test_add_auto_tags_and_quality_command(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "prompts.json"

            code, stdout, stderr = self.run_cli(
                "--data",
                str(data_path),
                "add",
                "Code reviewer",
                "--body",
                "Review Python code and output a Markdown table with bugs, edge cases, and missing tests.",
                "--auto-tags",
            )

            self.assertEqual(code, 0, stderr)
            self.assertIn("coding", stdout)

            code, stdout, stderr = self.run_cli("--data", str(data_path), "quality", "1")

            self.assertEqual(code, 0, stderr)
            self.assertIn("Quality score", stdout)

    def test_import_json_command(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "prompts.json"
            import_path = Path(directory) / "import.json"
            import_path.write_text(
                json.dumps({"prompts": [{"title": "Importer", "body": "Write a concise summary.", "tags": ["writing"]}]}),
                encoding="utf-8",
            )

            code, stdout, stderr = self.run_cli(
                "--data",
                str(data_path),
                "import",
                str(import_path),
                "--format",
                "json",
            )

            self.assertEqual(code, 0, stderr)
            self.assertIn("Imported 1 prompts", stdout)
            self.assertEqual(PromptStore(data_path).get(1).title, "Importer")


if __name__ == "__main__":
    unittest.main()
