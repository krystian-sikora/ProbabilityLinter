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
    return errors


def check_required_attrs(token: Token) -> list[LintError]:
    errors = []

    for attr in REQUIRED_ATTRS.get(token.tag, set()):
        if attr in token.attrs and token.attrs[attr]:
            continue

        errors.append(LintError(
            line=token.line,
            col=token.col,
            offset=token.offset,
            tag=token.tag,
            message=f"Missing required attribute '{attr}'",
        ))

    return errors
