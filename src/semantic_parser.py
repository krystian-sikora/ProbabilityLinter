"""
Semantic parser: converts linted tokens into probability blocks,
wires them to PiterInterface, and returns diagnostics.
"""
from src.lint_error import LintError
from src.token_parser import attr_str
from src.tokenizer import Token
from src.scope_manager import ProbabilityBlock, build_blocks
from src.PiterInterface import (
    PiterInterface,
    PiterInterfaceError,
)


def _make_error(token: Token, message: str, severity: str = "error") -> LintError:
    return LintError(
        message=message,
        tag=token.tag,
        line=token.line,
        col=token.col,
        offset=token.offset,
        end_offset=token.end_offset,
        severity=severity,
    )


def _given(attrs: dict, default: str = "True") -> str:
    return attr_str(attrs, "given", default) or default


def validate_block(block: ProbabilityBlock) -> list[LintError]:
    """
    Feed a probability block through PiterInterface and collect diagnostics.
    """
    errors: list[LintError] = []
    pi = PiterInterface()
    prefix = f"block '{block.block_id}': " if block.block_id != "default" else ""

    symbols = [
        name
        for token in block.symbols
        if (name := attr_str(token.attrs, "name"))
    ]
    name_counts: dict[str, int] = {}
    for token in block.symbols:
        name = attr_str(token.attrs, "name")
        if name:
            name_counts[name] = name_counts.get(name, 0) + 1
    for token in block.symbols:
        name = attr_str(token.attrs, "name")
        if name and name_counts[name] > 1:
            errors.append(_make_error(
                token,
                prefix + f"Duplicate symbol '{name}'",
                severity="warning",
            ))
    if symbols:
        pi.set_symbols(symbols)

    for token in block.constraints:
        expr = attr_str(token.attrs, "expr")
        if not expr:
            continue
        try:
            pi.add_constraint(expr)
        except PiterInterfaceError as e:
            errors.append(_make_error(token, prefix + str(e)))

    declared_probs: list[tuple[Token, str, str]] = []
    for token in block.probabilities:
        target = attr_str(token.attrs, "target")
        value_raw = attr_str(token.attrs, "value")
        if not target or not value_raw:
            continue
        declared_probs.append((token, target, _given(token.attrs)))

    prob_key_counts: dict[tuple[str, str], int] = {}
    for _, target, given in declared_probs:
        key = (target, given)
        prob_key_counts[key] = prob_key_counts.get(key, 0) + 1
    for token, target, given in declared_probs:
        if prob_key_counts[(target, given)] > 1:
            errors.append(_make_error(
                token,
                prefix + f"Duplicate probability P({target} | {given})",
                severity="warning",
            ))

    for token in block.probabilities:
        target = attr_str(token.attrs, "target")
        value_raw = attr_str(token.attrs, "value")
        given = _given(token.attrs)
        if not target or not value_raw:
            continue
        try:
            value = float(value_raw)
        except ValueError:
            errors.append(_make_error(
                token,
                prefix + f"Probability value must be a number, got {value_raw!r}",
            ))
            continue
        if value in (0.0, 1.0):
            errors.append(_make_error(
                token,
                prefix + (
                    f"Probability value {value_raw} is 0 or 1; "
                    "this can cause mathematical problems"
                ),
                severity="warning",
            ))
        try:
            pi.add_probability(target, given, value)
        except PiterInterfaceError as e:
            errors.append(_make_error(token, prefix + str(e)))

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
                errors.append(_make_error(anchor, prefix + str(e)))

    for token in block.queries:
        target = attr_str(token.attrs, "target")
        given = _given(token.attrs)
        if not target:
            continue
        if not pi.is_solved:
            errors.append(_make_error(
                token,
                prefix + "Query skipped: probability block was not solved",
                severity="warning",
            ))
            continue
        try:
            result = pi.query(target, given)
            errors.append(_make_error(
                token,
                prefix + f"P({target} | {given}) = {result:.6f}",
                severity="info",
            ))
        except PiterInterfaceError as e:
            errors.append(_make_error(token, prefix + str(e)))

    return errors


def duplicate_block_id_warnings(tokens: list[Token]) -> list[LintError]:
    """Warn on every <block id="..."/> that reuses an explicit id in the document."""
    id_counts: dict[str, int] = {}
    for token in tokens:
        if token.tag != "block":
            continue
        block_id = attr_str(token.attrs, "id")
        if not block_id:
            continue
        id_counts[block_id] = id_counts.get(block_id, 0) + 1

    warnings: list[LintError] = []
    for token in tokens:
        if token.tag != "block":
            continue
        block_id = attr_str(token.attrs, "id")
        if block_id and id_counts[block_id] > 1:
            warnings.append(_make_error(
                token,
                f"Duplicate block id '{block_id}'",
                severity="warning",
            ))
    return warnings


def lint_semantic(tokens: list[Token]) -> list[LintError]:
    """
    Entry point used by linter.py and lsp.py.
    Builds blocks and validates each one.
    """
    errors: list[LintError] = []
    errors.extend(duplicate_block_id_warnings(tokens))
    for block in build_blocks(tokens):
        errors.extend(validate_block(block))
    return errors
