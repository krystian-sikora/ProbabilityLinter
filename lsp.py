from lsprotocol import types
from lsprotocol.types import (
    TEXT_DOCUMENT_DID_OPEN, TEXT_DOCUMENT_DID_CHANGE, TEXT_DOCUMENT_HOVER,
    Diagnostic, DiagnosticSeverity, Position, Range,
    DidOpenTextDocumentParams,
    Hover, HoverParams,
    MarkupContent, MarkupKind,
)
from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument

from src.token_parser import lint
from src.semantic_parser import lint_semantic
from src.tokenizer import scan


def _offset_to_position(source: str, offset: int) -> Position:
    """Convert a 0-based source index to an LSP Position (0-based line/character)."""
    line = source.count("\n", 0, offset)
    last_nl = source.rfind("\n", 0, offset)
    character = offset - last_nl - 1 if last_nl >= 0 else offset
    return Position(line=line, character=character)


def _diagnostic_range(source: str, error) -> Range:
    """Span the full tag when end_offset is known; otherwise point at line/col."""
    if error.end_offset is not None and error.end_offset > error.offset:
        return Range(
            start=_offset_to_position(source, error.offset),
            end=_offset_to_position(source, error.end_offset),
        )
    return Range(
        start=Position(line=error.line - 1, character=error.col - 1),
        end=Position(line=error.line - 1, character=error.col - 1),
    )


class ProbLinterServer(LanguageServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostics = {}

    def make_diagnostics(self, document: TextDocument) -> None:
        diagnostics = []
        result = scan(document.source)

        all_errors = list(result.errors)
        all_errors.extend(lint(result.tokens))
        all_errors.extend(lint_semantic(result.tokens))

        for error in all_errors:
            severity = {
                "error": DiagnosticSeverity.Error,
                "warning": DiagnosticSeverity.Warning,
                "info": DiagnosticSeverity.Information,
            }.get(error.severity, DiagnosticSeverity.Error)
            diagnostics.append(Diagnostic(
                range=_diagnostic_range(document.source, error),
                message=error.message,
                severity=severity,
                source="prob-linter",
            ))

        self.diagnostics[document.uri] = (document.version, diagnostics)


server = ProbLinterServer("prob-linter", "v0.1")


@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: ProbLinterServer, params: DidOpenTextDocumentParams):
    document = ls.workspace.get_text_document(params.text_document.uri)
    ls.make_diagnostics(document)

    for uri, (version, diagnostics) in ls.diagnostics.items():
        ls.text_document_publish_diagnostics(
            types.PublishDiagnosticsParams(
                uri=uri,
                version=version,
                diagnostics=diagnostics,
            )
        )


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: ProbLinterServer, params):
    document = ls.workspace.get_text_document(params.text_document.uri)
    ls.make_diagnostics(document)
    for uri, (version, diagnostics) in ls.diagnostics.items():
        ls.text_document_publish_diagnostics(
            types.PublishDiagnosticsParams(
                uri=uri,
                version=version,
                diagnostics=diagnostics,
            )
        )


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls: ProbLinterServer, params: HoverParams):
    """
    Return diagnostic messages for the current line as hover text.
    This enables `vim.lsp.buf.hover()` in Neovim to show linter errors.
    """
    document = ls.workspace.get_text_document(params.text_document.uri)

    # Ensure diagnostics are computed (e.g. if hover fires before didOpen)
    if document.uri not in ls.diagnostics:
        ls.make_diagnostics(document)

    _, diagnostics = ls.diagnostics.get(document.uri, (None, []))

    # Match diagnostics that span the cursor line
    line = params.position.line
    matching = [
        d for d in diagnostics
        if d.range.start.line <= line <= d.range.end.line
    ]

    if not matching:
        return None

    lines = [f"**{d.severity.name}**: {d.message}" for d in matching]
    contents = MarkupContent(kind=MarkupKind.Markdown, value="\n\n".join(lines))

    return Hover(
        contents=contents,
        range=Range(
            start=Position(line=line, character=0),
            end=Position(line=line, character=999),
        ),
    )


def start_server():
    server.start_io()


if __name__ == "__main__":
    start_server()
