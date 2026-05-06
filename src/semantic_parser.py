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
    SymbolError,
    ProbabilityValueError,
    InconsistentSystemError,
    UnderdeterminedSystemError,
    InvalidSolutionError,
    ImpossibleConditionError,
)


@dataclass
class ProbabilityBlock:
    """A group of related tags that form one probability system."""
    tokens: list[Token]

    @property
    def statements(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "statement"]

    @property
    def constraints(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "constraint"]

    @property
    def probabilities(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "probability"]

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


def validate_block(block: ProbabilityBlock) -> list[LintError]:
    """
    Feed a probability block through PiterInterface and collect diagnostics.
    """
    errors: list[LintError] = []
    pi = PiterInterface()

    # Register symbols from statements
    symbols = []
    for token in block.statements:
        s = token.attrs.get("s", "").strip()
        if s:
            symbols.append(s)
    if symbols:
        pi.set_symbols(symbols)

    # Add constraints
    for token in block.constraints:
        c = token.attrs.get("c", "").strip()
        if not c:
            continue
        try:
            pi.add_constraint(c)
        except PiterInterfaceError as e:
            errors.append(_make_error(token, str(e)))

    # Add probabilities
    for token in block.probabilities:
        t = token.attrs.get("t", "").strip()
        c = token.attrs.get("c", "True").strip() or "True"
        p_raw = token.attrs.get("p", "").strip()
        if not t or not p_raw:
            continue  # syntactic errors already caught by token_parser
        try:
            p = float(p_raw)
            pi.add_probability(t, c, p)
        except PiterInterfaceError as e:
            errors.append(_make_error(token, str(e)))

    # Solve the system (triggered by queries, or by the presence of probabilities)
    if block.probabilities or block.queries:
        try:
            pi.solve()
        except PiterInterfaceError as e:
            # Attach to the first token that contributed to the block
            # (or the first token overall if none)
            anchor = block.probabilities[0] if block.probabilities else (
                block.constraints[0] if block.constraints else (
                    block.tokens[0] if block.tokens else None
                )
            )
            if anchor:
                errors.append(_make_error(anchor, str(e)))

    # Execute queries
    for token in block.queries:
        t = token.attrs.get("t", "").strip()
        c = token.attrs.get("c", "True").strip() or "True"
        if not t:
            continue
        try:
            result = pi.query(t, c)
            errors.append(_make_error(
                token,
                f"P({t} | {c}) = {result:.6f}",
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
