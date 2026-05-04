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
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required attribute 'p'", errors[0].message)
        self.assertEqual(errors[0].tag, "probability")

    def test_all_tags_missing_attributes(self):
        source = (
            "<statement>Stmt</statement>\n"
            "<constraint>Constr</constraint>\n"
            "<probability>Prob</probability>"
        )
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 3)
        messages = {e.message for e in errors}
        self.assertIn("Missing required attribute 's'", messages)
        self.assertIn("Missing required attribute 'c'", messages)
        self.assertIn("Missing required attribute 'p'", messages)

    def test_statement_with_s_no_error(self):
        source = "<statement s='d'>Two infants are dead.</statement>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)

    def test_constraint_with_c_no_error(self):
        source = "<constraint c='~(~d & m)'>Logical constraint.</constraint>"
        errors = lint(tokenize(source))
        self.assertEqual(len(errors), 0)

    def test_probability_with_p_no_error(self):
        source = "<probability p='0.0001'>The probability is low.</probability>"
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


if __name__ == "__main__":
    unittest.main()
