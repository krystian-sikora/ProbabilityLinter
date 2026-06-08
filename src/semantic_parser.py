"""
Semantic parser: converts linted tokens into probability blocks,
wires them to PiterInterface, and returns diagnostics.
"""
from dataclasses import dataclass

from src.token_parser import LintError
from src.tokenizer import Token
from src.PiterInterface import (
    PiterInterface,
    PiterInterfaceError,
)


@dataclass
class ProbabilityBlock:
    """A group of related tags that form one probability system."""
    tokens: list[Token]

    @property
    def symbols(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "symbol"]

    @property
    def constraints(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "constraint"]

    @property
    def probabilities(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "prob"]

    @property
    def queries(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "query"]


def build_blocks(tokens: list[Token]) -> list[ProbabilityBlock]:
    """
    Currently the whole document is one block.
    Future: split by blank lines, headers, or explicit delimiters.
    """
    return [ProbabilityBlock(tokens=tokens)]


def _make_error(token: Token, message: str, severity: str = "error") -> LintError:
    return LintError(
        message=message,
        tag=token.tag,
        line=token.line,
        col=token.col,
        offset=token.offset,
        severity=severity,
    )


def _given(attrs: dict, default: str = "True") -> str:
    return attrs.get("given", default).strip() or default


def validate_block(block: ProbabilityBlock) -> list[LintError]:
    """
    Feed a probability block through PiterInterface and collect diagnostics.
    """
    errors: list[LintError] = []
    pi = PiterInterface()

    symbols = [
        token.attrs.get("name", "").strip()
        for token in block.symbols
        if token.attrs.get("name", "").strip()
    ]
    if symbols:
        pi.set_symbols(symbols)

    for token in block.constraints:
        expr = token.attrs.get("expr", "").strip()
        if not expr:
            continue
        try:
            pi.add_constraint(expr)
        except PiterInterfaceError as e:
            errors.append(_make_error(token, str(e)))

    for token in block.probabilities:
        target = token.attrs.get("target", "").strip()
        value_raw = token.attrs.get("value", "").strip()
        given = _given(token.attrs)
        if not target or not value_raw:
            continue
        try:
            pi.add_probability(target, given, float(value_raw))
        except PiterInterfaceError as e:
            errors.append(_make_error(token, str(e)))

    if pi.piter is not None and (block.probabilities or block.queries):
        try:
            pi.solve()
        except PiterInterfaceError as e:
            anchor = block.probabilities[0] if block.probabilities else (
                block.constraints[0] if block.constraints else (
                    block.tokens[0] if block.tokens else None
                )
            )
            if anchor:
                errors.append(_make_error(anchor, str(e)))

    for token in block.queries:
        target = token.attrs.get("target", "").strip()
        given = _given(token.attrs)
        if not target or not pi.is_solved:
            continue
        try:
            result = pi.query(target, given)
            errors.append(_make_error(
                token,
                f"P({target} | {given}) = {result:.6f}",
                severity="info",
            ))
        except PiterInterfaceError as e:
            errors.append(_make_error(token, str(e)))

    return errors


def lint_semantic(tokens: list[Token]) -> list[LintError]:
    """
    Entry point used by linter.py and lsp.py.
    Builds blocks and validates each one.
    """
    errors: list[LintError] = []
    for block in build_blocks(tokens):
        errors.extend(validate_block(block))
    return errors
