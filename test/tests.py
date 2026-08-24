import unittest

from src.lint_error import LintError
from src.token_parser import lint
from src.tokenizer import tokenize
from src.scope_manager import build_blocks
from linter import lint_source


class TestMissingAttributes(unittest.TestCase):
    """Tests for missing required attributes."""

    def test_symbol_missing_name(self):
        source = "<symbol>Two infants are dead.</symbol>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 'name'", errors[0].message)
        self.assertEqual(errors[0].tag, "symbol")

    def test_constraint_missing_expr(self):
        source = "<constraint />"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 'expr'", errors[0].message)
        self.assertEqual(errors[0].tag, "constraint")

    def test_prob_missing_value(self):
        source = "<prob target='m' />"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 'value'", errors[0].message)

    def test_prob_missing_target(self):
        source = "<prob value='0.0001' />"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 'target'", errors[0].message)

    def test_all_tags_missing_required(self):
        source = (
            "<symbol>Stmt</symbol>\n"
            "<constraint />\n"
            "<prob />"
        )
        errors = lint(tokenize(source))
        messages = {e.message for e in errors}
        self.assertIn("Missing required attribute 'name'", messages)
        self.assertIn("Missing required attribute 'expr'", messages)
        self.assertIn("Missing required attribute 'target'", messages)
        self.assertIn("Missing required attribute 'value'", messages)

    def test_symbol_with_name_no_error(self):
        source = "<symbol name='d'>Two infants are dead.</symbol>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)

    def test_constraint_with_expr_no_error(self):
        source = "<constraint expr='~(~d & m)' />"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)

    def test_prob_self_closing_no_error(self):
        source = "<prob target='d' value='0.0001' />"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)

    def test_empty_attribute_value_is_error(self):
        source = "<symbol name=''>Empty name.</symbol>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 'name'", errors[0].message)

    def test_line_and_col_reported(self):
        source = "line1\n<symbol>missing</symbol>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].line, 2)
        self.assertEqual(errors[0].col, 1)

    def test_lint_source_returns_gcc_format(self):
        source = "<symbol>missing</symbol>"
        gcc = lint_source(source)
        self.assertEqual(len(gcc), 1)
        self.assertIn("<string>:1:1: error: Missing required attribute 'name'", gcc[0])

    def test_query_missing_target(self):
        source = "<query>What is P(m|d)?</query>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 'target'", errors[0].message)
        self.assertEqual(errors[0].tag, "query")

    def test_query_self_closing_no_error(self):
        source = "<query target='m' given='d' />"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)

    def test_block_self_closing_no_error(self):
        source = "<block id='case-a' />"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)

    def test_block_must_be_self_closing(self):
        source = "<block></block>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("self-closing", errors[0].message)

    def test_incomplete_attribute_does_not_crash(self):
        """Partial tags while typing (e.g. <prob value=/>) must not raise AttributeError."""
        source = "<prob value=/>"
        gcc = lint_source(source)
        messages = " ".join(gcc)
        self.assertIn("Missing required attribute 'target'", messages)
        self.assertIn("Missing required attribute 'value'", messages)

    def test_unclosed_constraint_emits_warning(self):
        source = (
            "<block id='test' />\n"
            "<prob target='a' value='0.5' />\n"
            "<constraint expr='~(a & m)'>\n"
            "<query target='a' given='m' />"
        )
        gcc = lint_source(source)
        warnings = [line for line in gcc if ": warning:" in line]
        self.assertEqual(len(warnings), 1)
        self.assertIn("Unclosed <constraint>", warnings[0])

    def test_closed_symbol_no_unclosed_warning(self):
        source = "<symbol name='d'>Two infants are dead.</symbol>"
        gcc = lint_source(source)
        warnings = [line for line in gcc if ": warning:" in line]
        self.assertEqual(len(warnings), 0)

    def test_self_closing_constraint_no_unclosed_warning(self):
        source = "<constraint expr='~(a & m)' />"
        gcc = lint_source(source)
        warnings = [line for line in gcc if ": warning:" in line]
        self.assertEqual(len(warnings), 0)

    def test_wrong_attribute_name_still_tokenizes(self):
        """Wrong attr name should not silently skip the tag."""
        source = "<constraint c='~(~d & m)' />"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 'expr'", errors[0].message)

    def test_token_end_offset_spans_full_tag(self):
        source = "<prob target='d' value='0.5' />"
        token = tokenize(source)[0]
        self.assertEqual(source[token.offset:token.end_offset], source[token.offset:].strip())
        self.assertTrue(source[token.offset:token.end_offset].endswith("/>"))


class TestBlockScoping(unittest.TestCase):
    """Tests for <block /> probability block boundaries."""

    def test_no_block_tag_is_single_default_block(self):
        source = (
            "<prob target='d' value='0.5' />\n"
            "<query target='d' />"
        )
        blocks = build_blocks(tokenize(source))
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].block_id, "default")
        self.assertEqual(len(blocks[0].probabilities), 1)

    def test_block_anchor_splits_into_two_blocks(self):
        source = (
            "<block id='a' />\n"
            "<prob target='d' value='0.1' />\n"
            "<block id='b' />\n"
            "<prob target='d' value='0.2' />\n"
        )
        blocks = build_blocks(tokenize(source))
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].block_id, "a")
        self.assertEqual(blocks[1].block_id, "b")
        self.assertEqual(len(blocks[0].probabilities), 1)
        self.assertEqual(len(blocks[1].probabilities), 1)

    def test_tags_before_first_block_go_to_default(self):
        source = (
            "<prob target='d' value='0.5' />\n"
            "<block id='second' />\n"
            "<prob target='d' value='0.5' />\n"
        )
        blocks = build_blocks(tokenize(source))
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].block_id, "default")
        self.assertEqual(blocks[1].block_id, "second")

    def test_contradiction_is_scoped_to_one_block(self):
        source = (
            "<block id='ok' />\n"
            "<prob target='d' value='0.1' />\n"
            "<query target='d' />\n"
            "<block id='bad' />\n"
            "<prob target='d' value='0.2' />\n"
            "<prob target='d' value='0.3' />\n"
        )
        gcc = lint_source(source)
        info_lines = [line for line in gcc if ": info:" in line]
        error_lines = [line for line in gcc if ": error:" in line]
        self.assertEqual(len(info_lines), 1)
        self.assertIn("block 'ok'", info_lines[0])
        self.assertTrue(any("block 'bad'" in line and "contradictory" in line.lower() for line in error_lines))


class TestSemanticLinting(unittest.TestCase):
    """Integration tests for the semantic parser wired to PiterInterface."""

    def test_valid_probability_block_emits_query_result(self):
        source = (
            "<symbol name='d'>Two infants are dead.</symbol>\n"
            "<symbol name='m'>Mother is a murderer.</symbol>\n"
            "<constraint expr='~(~d & m)' />\n"
            "<prob target='m' value='0.0001' />\n"
            "<prob target='d' value='0.001' />\n"
            "<query target='m' given='d' />"
        )
        gcc = lint_source(source)
        info_lines = [line for line in gcc if ": info:" in line]
        self.assertEqual(len(info_lines), 1)
        self.assertIn("P(m | d) = 0.1", info_lines[0])

    def test_contradictory_system_emits_error(self):
        source = (
            "<prob target='d' value='0.1' />\n"
            "<prob target='d' value='0.2' />\n"
            "<query target='d' />"
        )
        gcc = lint_source(source)
        error_lines = [line for line in gcc if ": error:" in line]
        self.assertTrue(any("contradictory" in line.lower() for line in error_lines))

    def test_probability_out_of_range_emits_error(self):
        source = (
            "<prob target='d' value='1.5' />\n"
            "<query target='d' />"
        )
        gcc = lint_source(source)
        error_lines = [line for line in gcc if ": error:" in line]
        self.assertTrue(any("1.5" in line for line in error_lines))

    def test_invalid_sympy_expression_emits_error(self):
        source = (
            "<constraint expr='d @@@ m' />\n"
            "<query target='d' />"
        )
        gcc = lint_source(source)
        error_lines = [line for line in gcc if ": error:" in line]
        self.assertTrue(any("parse" in line.lower() for line in error_lines))

    def test_duplicate_symbol_emits_warning(self):
        source = (
            "<symbol name='d'>First.</symbol>\n"
            "<symbol name='d'>Second.</symbol>\n"
            "<prob target='d' value='0.5' />\n"
            "<query target='d' />"
        )
        gcc = lint_source(source)
        warning_lines = [line for line in gcc if ": warning:" in line]
        self.assertEqual(len(warning_lines), 2)
        self.assertTrue(all("Duplicate symbol 'd'" in line for line in warning_lines))
        self.assertTrue(any(line.startswith("<string>:1:") for line in warning_lines))
        self.assertTrue(any(line.startswith("<string>:2:") for line in warning_lines))
        info_lines = [line for line in gcc if ": info:" in line]
        self.assertEqual(len(info_lines), 1)

    def test_same_symbol_name_in_separate_blocks_no_warning(self):
        source = (
            "<block id='a' />\n"
            "<symbol name='d'>In block a.</symbol>\n"
            "<prob target='d' value='0.3' />\n"
            "<query target='d' />\n"
            "<block id='b' />\n"
            "<symbol name='d'>In block b.</symbol>\n"
            "<prob target='d' value='0.4' />\n"
            "<query target='d' />"
        )
        gcc = lint_source(source)
        warning_lines = [line for line in gcc if ": warning:" in line]
        self.assertEqual(warning_lines, [])


if __name__ == "__main__":
    unittest.main()
