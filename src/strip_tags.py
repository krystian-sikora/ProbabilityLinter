"""Remove prob-linter tag markup from Markdown source."""

from src.tokenizer import Token, scan


def _replacement_span(source: str, token: Token) -> tuple[int, int, str]:
    """Return (start, end, replacement) for *token*, optionally swallowing an empty line."""
    replacement = "" if token.self_closing else token.content
    start, end = token.offset, token.end_offset

    line_start = source.rfind("\n", 0, start) + 1
    line_end = source.find("\n", end)
    if line_end == -1:
        line_end = len(source)

    before = source[line_start:start]
    after = source[end:line_end]
    if not before.strip() and not after.strip() and not replacement.strip():
        start = line_start
        if line_end < len(source) and source[line_end] == "\n":
            end = line_end + 1
        else:
            end = line_end
        replacement = ""

    return start, end, replacement


def strip_tags(source: str) -> str:
    """
    Return *source* with known prob-linter tags removed.

    Self-closing tags (``<prob ... />``, ``<block ... />``, etc.) are deleted
    entirely. Paired tags (``<symbol ...>...</symbol>``) are replaced by their
    inner text so inline prose is preserved. When a tag is the only non-whitespace
    content on its line, the whole line (including the newline) is removed.
    Unknown ``<...>`` sequences are left unchanged.
    """
    result = scan(source)
    if not result.tokens:
        return source

    parts: list[str] = []
    cursor = 0
    for token in sorted(result.tokens, key=lambda t: t.offset):
        start, end, replacement = _replacement_span(source, token)
        parts.append(source[cursor:start])
        parts.append(replacement)
        cursor = end
    parts.append(source[cursor:])
    return "".join(parts)
