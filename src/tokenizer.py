import re
from dataclasses import dataclass
from typing import Any

KNOWN_TAGS = {"block", "prob", "constraint", "query", "symbol"}

TAG_RE = re.compile(
    r'<(?P<tag>' + '|'.join(KNOWN_TAGS) + r')'
    r'(?P<attrs>[^>]*)'
    r'(?:>(?P<content>.*?)</(?P=tag)>|\s*/>)',
    re.DOTALL,
)

ATTR_RE = re.compile(r'(?P<key>[\w-]+)(?:=(?P<quote>["\'])(?P<value>.*?)(?P=quote))?')


@dataclass
class Token:
    tag: str
    attrs: dict[str, Any]
    content: str
    line: int
    col: int
    offset: int
    self_closing: bool = False


def tokenize(source: str) -> list[Token]:
    """
    Extract prob-linter tags from Markdown source.
    Supports paired tags and self-closing tags (e.g. <prob target="m" value="0.5" />).
    """
    tokens = []

    for match in TAG_RE.finditer(source):
        offset = match.start()
        line = source[:offset].count('\n') + 1
        col = offset - source.rfind('\n', 0, offset)
        attrs = {
            m.group('key'): m.group('value')
            for m in ATTR_RE.finditer(match.group('attrs'))
        }
        content = match.group('content')
        tokens.append(Token(
            tag=match.group('tag'),
            attrs=attrs,
            content=content.strip() if content else '',
            line=line,
            col=col,
            offset=offset,
            self_closing=content is None,
        ))
    return tokens
