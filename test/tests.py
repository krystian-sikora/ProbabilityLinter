import unittest

from src.token_parser import lint, LintError
from src.tokenizer import tokenize
from linter import lint_source


class TestMissingAttributes(unittest.TestCase):
    """Tests for missing required attributes in custom XML-like tags."""

    def test_statement_missing_s(self):
        source = "<statement>Two infants are dead.</statement>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 's'", errors[0].message)
        self.assertEqual(errors[0].tag, "statement")

    def test_constraint_missing_c(self):
        source = "<constraint>If the two infants are not dead, the mother is not a murderer.</constraint>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 'c'", errors[0].message)
        self.assertEqual(errors[0].tag, "constraint")

    def test_probability_missing_p(self):
        source = "<probability>The probability is low.</probability>"
        errors = lint(tokenize(source))
        # probability now requires both 't' and 'p'
        self.assertEqual(len(errors), 2)
        messages = {e.message for e in errors}
        self.assertIn("Missing required attribute 'p'", messages)
        self.assertIn("Missing required attribute 't'", messages)

    def test_probability_missing_t(self):
        source = "<probability p='0.0001'>The probability is low.</probability>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 't'", errors[0].message)
        self.assertEqual(errors[0].tag, "probability")

    def test_all_tags_missing_attributes(self):
        source = (
            "<statement>Stmt</statement>\n"
            "<constraint>Constr</constraint>\n"
            "<probability>Prob</probability>"
        )
        errors = lint(tokenize(source))
        # 1 (statement s) + 1 (constraint c) + 2 (probability t+p) = 4
        self.assertEqual(len(errors), 4)
        messages = {e.message for e in errors}
        self.assertIn("Missing required attribute 's'", messages)
        self.assertIn("Missing required attribute 'c'", messages)
        self.assertIn("Missing required attribute 'p'", messages)
        self.assertIn("Missing required attribute 't'", messages)

    def test_statement_with_s_no_error(self):
        source = "<statement s='d'>Two infants are dead.</statement>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)

    def test_constraint_with_c_no_error(self):
        source = "<constraint c='~(~d & m)'>Logical constraint.</constraint>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)

    def test_probability_with_t_and_p_no_error(self):
        source = "<probability t='d' p='0.0001'>The probability is low.</probability>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)

    def test_empty_attribute_value_is_error(self):
        source = "<statement s=''>Empty s.</statement>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 's'", errors[0].message)

    def test_line_and_col_reported(self):
        source = "line1\n<statement>missing</statement>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        # Should be on line 2, column 1 (0-indexed offset logic)
        self.assertEqual(errors[0].line, 2)
        self.assertEqual(errors[0].col, 1)

    def test_lint_source_returns_gcc_format(self):
        source = "<statement>missing</statement>"
        gcc = lint_source(source)
        self.assertEqual(len(gcc), 1)
        self.assertIn("<string>:1:1: error: Missing required attribute 's'", gcc[0])

    def test_query_missing_t(self):
        source = "<query>What is P(m|d)?</query>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 't'", errors[0].message)
        self.assertEqual(errors[0].tag, "query")

    def test_query_with_t_no_error(self):
        source = "<query t='m' c='d'>What is P(m|d)?</query>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)


class TestSemanticLinting(unittest.TestCase):
    """Integration tests for the semantic parser wired to PiterInterface."""

    def test_valid_probability_block_emits_query_result(self):
        source = (
            "<statement s='d'>Two infants are dead.</statement>\n"
            "<statement s='m'>Mother is a murderer.</statement>\n"
            "<constraint c='~(~d & m)'>If infants not dead, mother not murderer.</constraint>\n"
            "<probability t='m' p='0.0001'>P(m) = 0.01%</probability>\n"
            "<probability t='d' p='0.001'>P(d) = 0.1%</probability>\n"
            "<query t='m' c='d'>What is P(m|d)?</query>"
        )
        gcc = lint_source(source)
        # Should contain an info diagnostic with the computed probability
        info_lines = [line for line in gcc if ": info:" in line]
        self.assertEqual(len(info_lines), 1)
        self.assertIn("P(m | d) = 0.1", info_lines[0])

    def test_contradictory_system_emits_error(self):
        source = (
            "<statement s='d'>Two infants are dead.</statement>\n"
            "<probability t='d' p='0.1'>P(d) = 0.1</probability>\n"
            "<probability t='d' p='0.2'>P(d) = 0.2</probability>\n"
            "<query t='d'>What is P(d)?</query>"
        )
        gcc = lint_source(source)
        error_lines = [line for line in gcc if ": error:" in line]
        self.assertTrue(any("contradictory" in line.lower() for line in error_lines))

    def test_probability_out_of_range_emits_error(self):
        source = (
            "<statement s='d'>Two infants are dead.</statement>\n"
            "<probability t='d' p='1.5'>P(d) = 150%</probability>\n"
            "<query t='d'>What is P(d)?</query>"
        )
        gcc = lint_source(source)
        error_lines = [line for line in gcc if ": error:" in line]
        self.assertTrue(any("1.5" in line for line in error_lines))

    def test_invalid_sympy_expression_emits_error(self):
        source = (
            "<statement s='d'>Two infants are dead.</statement>\n"
            "<constraint c='d @@@ m'>Nonsense constraint.</constraint>\n"
            "<query t='d'>What is P(d)?</query>"
        )
        gcc = lint_source(source)
        error_lines = [line for line in gcc if ": error:" in line]
        self.assertTrue(any("parse" in line.lower() for line in error_lines))


if __name__ == "__main__":
    unittest.main()
