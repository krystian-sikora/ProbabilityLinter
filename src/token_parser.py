from dataclasses import dataclass

from src.tokenizer import Token

@dataclass
class LintError:
    message: str
    tag: str
    line: int
    col: int
    offset: int

REQUIRED_ATTRS: dict[str, set[str]] = {
    "statement": {"s"},
    "constraint": {"c"},
    "probability": {"p"},
}

def lint(tokens: list[Token]) -> list[LintError]:
    errors = []
    for token in tokens:
        errors.extend(check_required_attrs(token))
        # errors.extend(check_content(token))
    return errors


def check_required_attrs(token: Token) -> list[LintError]:
    errors = []
    for attr in REQUIRED_ATTRS.get(token.tag, set()):
        errors.append(LintError(
            line = token.line,
            col = token.col,
            offset = token.offset,
            tag = token.tag,
            message=f"Missing required attribute '{attr}'"),
        )
        if attr not in token.attrs:
            pass
    return errors