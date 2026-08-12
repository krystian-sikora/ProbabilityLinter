"""Shared lint pipeline used by CLI and LSP adapters."""

from src.lint_error import LintError
from src.semantic_parser import lint_semantic
from src.token_parser import lint
from src.tokenizer import scan


def collect_errors(source: str) -> list[LintError]:
    """Run scan → lint → lint_semantic and return all LintError values."""
    result = scan(source)
    errors = list(result.errors)
    errors.extend(lint(result.tokens))
    errors.extend(lint_semantic(result.tokens))
    return errors
