import re
from dataclasses import dataclass

from src.tokenizer import KNOWN_TAGS, Token

_OPEN_TAG_RE = re.compile(
    r'<(?P<tag>' + '|'.join(KNOWN_TAGS) + r')(?P<attrs>[^>]*)>',
)
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


def _position(source: str, offset: int) -> tuple[int, int]:
    line = source[:offset].count('\n') + 1
    col = offset - source.rfind('\n', 0, offset)
    return line, col


def lint_unclosed_tags(source: str) -> list[LintError]:
    """
    Warn on prob-linter opening tags that are neither self-closed nor paired
    with a matching closing tag. These are ignored by the tokenizer.
    """
    errors: list[LintError] = []

    for match in _OPEN_TAG_RE.finditer(source):
        tag = match.group('tag')
        attrs = match.group('attrs')
        offset = match.start()
        line, col = _position(source, offset)

        if attrs.rstrip().endswith('/'):
            continue

        close_re = re.compile(r'</' + re.escape(tag) + r'\s*>')
        if close_re.search(source, match.end()):
            continue

        errors.append(LintError(
            message=(
                f"Unclosed <{tag}> tag: use '<{tag} ... />' or add '</{tag}>'"
            ),
            tag=tag,
            line=line,
            col=col,
            offset=offset,
            severity="warning",
        ))

    return errors


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
