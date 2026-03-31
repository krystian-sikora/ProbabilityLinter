import re
from dataclasses import dataclass
from typing import Any

KNOWN_TAGS = {"statement", "constraint", "probability"}

TAG_RE = re.compile(
    r'<(?P<tag>' + '|'.join(KNOWN_TAGS) + r')'  # opening tag name
    r'(?P<attrs>[^>]*)'                         # raw attributes
    r'>(?P<content>.*?)</(?P=tag)>',            # content + matching close tag
    re.DOTALL
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


def tokenize(source: str) -> list[Token]:
    """
    Method to tokenize the text of the Markdown file.
    :param source: Markdown file content to be tokenized.
    :return: list of Token objects
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
        tokens.append(Token(
            tag=match.group('tag'),
            attrs=attrs,
            content=match.group('content').strip(),
            line=line,
            col=col,
            offset=offset
        ))
    return tokens
