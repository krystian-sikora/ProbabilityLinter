from dataclasses import dataclass

from src.tokenizer import Token

# todo: nie można dodać zerwego lub pewnego prawdopodobieństwa - tworzy to problemy matematyczne

@dataclass
class LintError:
    message: str
    tag: str
    line: int
    col: int
    offset: int
    severity: str = "error"   # "error" | "warning" | "info"

def attr_str(attrs: dict, key: str, default: str = "") -> str:
    """Return a stripped attribute value; safe when the key is missing or None."""
    value = attrs.get(key)
    if value is None:
        return default
    return str(value).strip()


REQUIRED_ATTRS: dict[str, set[str]] = {
    "symbol": {"name"},
    "constraint": {"expr"},
    "prob": {"target", "value"},
    "query": {"target"},
}


def lint(tokens: list[Token]) -> list[LintError]:
    errors = []
    for token in tokens:
        errors.extend(check_required_attrs(token))
        errors.extend(check_block_tag(token))
    return errors

def check_block_tag(token: Token) -> list[LintError]:
    if token.tag != "block" or token.self_closing:
        return []

    return [LintError(
        line=token.line,
        col=token.col,
        offset=token.offset,
        tag=token.tag,
        message="Block tag must be self-closing: <block /> or <block id=\"name\" />",
    )]


def check_required_attrs(token: Token) -> list[LintError]:
    errors = []

    for attr in REQUIRED_ATTRS.get(token.tag, set()):
        if attr_str(token.attrs, attr):
            continue

        errors.append(LintError(
            line=token.line,
            col=token.col,
            offset=token.offset,
            tag=token.tag,
            message=f"Missing required attribute '{attr}'",
        ))

    return errors
