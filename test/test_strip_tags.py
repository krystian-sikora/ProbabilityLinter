import tempfile
import unittest
from pathlib import Path

from src.strip_tags import strip_tags


class TestStripTags(unittest.TestCase):
    def test_removes_self_closing_tags(self):
        source = (
            "Intro\n"
            '<constraint expr="~(~d & m)" />\n'
            '<prob target="m" value="0.0001" />\n'
            "Outro"
        )
        cleaned = strip_tags(source)
        self.assertEqual(cleaned, "Intro\nOutro")

    def test_keeps_paired_symbol_content(self):
        source = 'Evaluating if the <symbol name="m">mother is a murderess</symbol>.'
        cleaned = strip_tags(source)
        self.assertEqual(cleaned, "Evaluating if the mother is a murderess.")

    def test_removes_self_closing_symbol(self):
        source = '<symbol name="d" />\nParagraph.'
        cleaned = strip_tags(source)
        self.assertEqual(cleaned, "Paragraph.")

    def test_leaves_unknown_tags(self):
        source = "<custom attr='x'>keep me</custom>"
        cleaned = strip_tags(source)
        self.assertEqual(cleaned, source)

    def test_removes_block_anchor(self):
        source = '<block id="case-1" />\n\n## Heading'
        cleaned = strip_tags(source)
        self.assertEqual(cleaned, "\n## Heading")

    def test_keeps_paired_symbol_on_own_line(self):
        source = '<symbol name="d">Two infants are dead.</symbol>\n\nNext.'
        cleaned = strip_tags(source)
        self.assertEqual(cleaned, "Two infants are dead.\n\nNext.")

    def test_empty_source(self):
        self.assertEqual(strip_tags(""), "")


class TestStripTagsCli(unittest.TestCase):
    def test_cli_writes_output_file(self):
        from linter import parse_args, run_strip_tags

        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "in.md"
            out = Path(tmp) / "out.md"
            inp.write_text(
                '<block id="x" />\nHello <symbol name="a">world</symbol>.\n',
                encoding="utf-8",
            )
            args = parse_args(["-strip", "-f", str(inp), "-o", str(out)])
            run_strip_tags(args)
            self.assertEqual(
                out.read_text(encoding="utf-8"),
                "Hello world.\n",
            )


if __name__ == "__main__":
    unittest.main()
