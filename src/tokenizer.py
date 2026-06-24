from dataclasses import dataclass
from typing import Any

from src.lint_error import LintError

KNOWN_TAGS = {"block", "prob", "constraint", "query", "symbol"}


@dataclass
class Token:
    """One prob-linter tag extracted from Markdown source."""

    tag: str
    attrs: dict[str, Any]
    content: str
    line: int          # 1-based line of the opening '<'
    col: int           # 1-based column of the opening '<' on that line
    offset: int        # 0-based index of the opening '<' in the source
    end_offset: int    # 0-based index after the closing '/>' or '</tag>'
    self_closing: bool = False


@dataclass
class ScanResult:
    """Output of a single scan pass over the source."""

    tokens: list[Token]
    errors: list[LintError]


class _Scanner:
    """
    Hand-written lexer for prob-linter tags embedded in Markdown.

    Walks the source left-to-right. On '<', attempts to parse a known tag
    (block, prob, constraint, query, symbol). Plain text and unknown '<...'
    sequences are skipped. Structural failures produce LintError diagnostics
    and scanning continues from a recovery point.
    """

    def __init__(self, source: str) -> None:
        """Initialize scanner state for *source*."""
        self.source = source
        self.length = len(source)
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []
        self.errors: list[LintError] = []

    def scan(self) -> ScanResult:
        """Scan the full source and return tokens plus structural errors."""
        while self.pos < self.length:
            if self.source[self.pos] == "<":
                self._try_parse_tag()
            else:
                self._advance()
        return ScanResult(tokens=self.tokens, errors=self.errors)

    def _try_parse_tag(self) -> None:
        """
        Parse a tag starting at the current '<'.

        Emits a Token on success. On failure, appends a LintError and advances
        the cursor to a safe sync point so the rest of the file is still scanned.
        """
        start = self.pos
        start_line, start_col = self.line, self.col
        self._advance()  # '<'

        tag = self._read_tag_name()
        if tag is None:
            return

        attrs, attr_errors = self._parse_attrs(tag, start, start_line, start_col)
        self.errors.extend(attr_errors)

        if self._at_end():
            self.errors.append(self._error(
                tag, start, start_line, start_col,
                "Unclosed tag header: missing '>' or '/>'",
                "error",
            ))
            return

        self._skip_whitespace()
        if self._peek() == "/":
            self._advance()
            if not self._consume(">"):
                self.errors.append(self._error(
                    tag, start, start_line, start_col,
                    "Expected '>' after '/>'",
                    "error",
                ))
                self._skip_to(">")
                if self._peek() == ">":
                    self._advance()
            end = self.pos
            self.tokens.append(Token(
                tag=tag,
                attrs=attrs,
                content="",
                line=start_line,
                col=start_col,
                offset=start,
                end_offset=end,
                self_closing=True,
            ))
            return

        if not self._consume(">"):
            self.errors.append(self._error(
                tag, start, start_line, start_col,
                "Expected '>' or '/>' to close tag header",
                "error",
            ))
            self._skip_to(">")
            if self._peek() == ">":
                self._advance()
            return

        content_start = self.pos
        close = f"</{tag}>"
        close_idx = self.source.find(close, self.pos)
        if close_idx == -1:
            self.errors.append(self._error(
                tag, start, start_line, start_col,
                f"Unclosed <{tag}> tag: use '<{tag} ... />' or add '</{tag}>'",
                "warning",
                end_offset=content_start,
            ))
            return

        content = self.source[content_start:close_idx]
        self.pos = close_idx + len(close)
        self._sync_position_from(close_idx + len(close))
        end = self.pos

        self.tokens.append(Token(
            tag=tag,
            attrs=attrs,
            content=content.strip(),
            line=start_line,
            col=start_col,
            offset=start,
            end_offset=end,
            self_closing=False,
        ))

    def _read_tag_name(self) -> str | None:
        """
        Read an alphabetic tag name after '<'.

        Returns the name when it is in KNOWN_TAGS. Unknown names produce a
        warning and None; a bare '<' not followed by letters also returns None.
        """
        name_start = self.pos
        while self.pos < self.length and self.source[self.pos].isalpha():
            self._advance()
        name = self.source[name_start:self.pos]
        if name not in KNOWN_TAGS:
            if name:
                name_line = self.source.count("\n", 0, name_start) + 1
                last_nl = self.source.rfind("\n", 0, name_start)
                name_col = name_start - last_nl if last_nl >= 0 else name_start + 1
                self._skip_to(">")
                if self._peek() == ">":
                    self._advance()
                self.errors.append(LintError(
                    message=f"Unknown tag '{name}'",
                    tag=name,
                    line=name_line,
                    col=name_col,
                    offset=name_start - 1,  # include opening '<'
                    end_offset=self.pos,
                    severity="warning",
                ))
            return None
        return name

    def _parse_attrs(
        self,
        tag: str,
        tag_start: int,
        tag_line: int,
        tag_col: int,
    ) -> tuple[dict[str, str], list[LintError]]:
        """
        Parse attributes until '/', '>', or end of input.

        Keys without '=' are stored with an empty string value. Values must be
        single- or double-quoted; malformed quotes are reported but parsing
        continues best-effort.
        """
        attrs: dict[str, str] = {}
        errors: list[LintError] = []

        while not self._at_end():
            self._skip_whitespace()
            if self._at_end() or self._peek() in "/>":
                break

            key = self._read_attr_key()
            if not key:
                break

            self._skip_whitespace()
            if self._peek() != "=":
                attrs[key] = ""
                continue

            self._advance()  # '='
            if self._at_end() or self._peek() not in "'\"":
                errors.append(self._error(
                    tag, tag_start, tag_line, tag_col,
                    f"Expected quoted value for attribute '{key}'",
                    "warning",
                ))
                attrs[key] = ""
                continue

            quote = self._peek()
            self._advance()
            value, closed = self._read_quoted_value(quote)
            if not closed:
                errors.append(self._error(
                    tag, tag_start, tag_line, tag_col,
                    f"Unclosed quote in attribute '{key}'",
                    "warning",
                ))
            attrs[key] = value

        return attrs, errors

    def _read_attr_key(self) -> str:
        """Read a contiguous run of word characters and hyphens/underscores."""
        start = self.pos
        while self.pos < self.length:
            ch = self.source[self.pos]
            if ch.isalnum() or ch in "-_":
                self._advance()
            else:
                break
        return self.source[start:self.pos]

    def _read_quoted_value(self, quote: str) -> tuple[str, bool]:
        """
        Read characters until the matching *quote*.

        Returns (value, closed). *closed* is False when EOF is reached first.
        """
        start = self.pos
        while self.pos < self.length:
            ch = self.source[self.pos]
            if ch == quote:
                value = self.source[start:self.pos]
                self._advance()
                return value, True
            self._advance()
        return self.source[start:self.pos], False

    def _error(
        self,
        tag: str,
        offset: int,
        line: int,
        col: int,
        message: str,
        severity: str,
        end_offset: int | None = None,
    ) -> LintError:
        """Build a LintError anchored at the opening tag position."""
        return LintError(
            message=message,
            tag=tag,
            line=line,
            col=col,
            offset=offset,
            end_offset=end_offset,
            severity=severity,
        )

    def _peek(self) -> str:
        """Return the character at the cursor, or '' at EOF."""
        if self.pos >= self.length:
            return ""
        return self.source[self.pos]

    def _at_end(self) -> bool:
        """True when the cursor is past the last character."""
        return self.pos >= self.length

    def _consume(self, char: str) -> bool:
        """Advance past *char* when it matches the cursor; return whether it matched."""
        if self._peek() == char:
            self._advance()
            return True
        return False

    def _skip_whitespace(self) -> None:
        """Advance past spaces, tabs, and newlines."""
        while self.pos < self.length and self.source[self.pos].isspace():
            self._advance()

    def _skip_to(self, char: str) -> None:
        """Advance until *char* or EOF (used for error recovery)."""
        while self.pos < self.length and self.source[self.pos] != char:
            self._advance()

    def _advance(self) -> None:
        """Move the cursor forward by one character, updating line/col."""
        if self.pos >= self.length:
            return
        if self.source[self.pos] == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        self.pos += 1

    def _sync_position_from(self, pos: int) -> None:
        """Recompute line/col after jumping *pos* (e.g. after str.find())."""
        self.line = self.source.count("\n", 0, pos) + 1
        last_nl = self.source.rfind("\n", 0, pos)
        self.col = pos - last_nl if last_nl >= 0 else pos + 1


def scan(source: str) -> ScanResult:
    """
    Scan Markdown source for prob-linter tags in one pass.
    Returns successfully parsed tokens and structural/lexical errors.
    """
    return _Scanner(source).scan()


def tokenize(source: str) -> list[Token]:
    """
    Extract prob-linter tags from Markdown source.
    Supports paired tags and self-closing tags (e.g. <prob target="m" value="0.5" />).
    """
    return scan(source).tokens
