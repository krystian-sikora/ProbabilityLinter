import asyncio

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

LSP_DEBOUNCE_SECONDS = 0.5


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


def compute_diagnostics(source: str) -> list[Diagnostic]:
    """Run the full lint pipeline and return LSP diagnostics."""
    result = scan(source)

    all_errors = list(result.errors)
    all_errors.extend(lint(result.tokens))
    all_errors.extend(lint_semantic(result.tokens))

    diagnostics = []
    for error in all_errors:
        severity = {
            "error": DiagnosticSeverity.Error,
            "warning": DiagnosticSeverity.Warning,
            "info": DiagnosticSeverity.Information,
        }.get(error.severity, DiagnosticSeverity.Error)
        diagnostics.append(Diagnostic(
            range=_diagnostic_range(source, error),
            message=error.message,
            severity=severity,
            source="prob-linter",
        ))
    return diagnostics


class ProbLinterServer(LanguageServer):
    def __init__(self, *args, debounce_seconds: float = LSP_DEBOUNCE_SECONDS, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostics: dict[str, tuple[int | None, list[Diagnostic]]] = {}
        self._debounce_seconds = debounce_seconds
        self._debounce_tasks: dict[str, asyncio.Task] = {}

    def schedule_debounced_lint(self, uri: str) -> None:
        """Wait for a pause in edits, then lint and publish diagnostics."""
        loop = asyncio.get_running_loop()

        existing = self._debounce_tasks.pop(uri, None)
        if existing is not None:
            existing.cancel()

        async def _debounced() -> None:
            try:
                await asyncio.sleep(self._debounce_seconds)
                await self.lint_and_publish(uri)
            except asyncio.CancelledError:
                pass
            finally:
                if self._debounce_tasks.get(uri) is task:
                    self._debounce_tasks.pop(uri, None)

        task = loop.create_task(_debounced())
        self._debounce_tasks[uri] = task

    async def lint_and_publish(self, uri: str) -> None:
        """Lint *uri* in a worker thread and publish if the document is unchanged."""
        document = self.workspace.get_text_document(uri)
        version_at_start = document.version
        source = document.source

        loop = asyncio.get_running_loop()
        diagnostics = await loop.run_in_executor(
            self.thread_pool,
            compute_diagnostics,
            source,
        )

        document = self.workspace.get_text_document(uri)
        if document.version != version_at_start:
            return

        self.diagnostics[uri] = (document.version, diagnostics)
        self.text_document_publish_diagnostics(
            types.PublishDiagnosticsParams(
                uri=uri,
                version=document.version,
                diagnostics=diagnostics,
            )
        )


server = ProbLinterServer("prob-linter", "v0.1")


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: ProbLinterServer, params: DidOpenTextDocumentParams):
    await ls.lint_and_publish(params.text_document.uri)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls: ProbLinterServer, params):
    ls.schedule_debounced_lint(params.text_document.uri)


@server.feature(TEXT_DOCUMENT_HOVER)
async def hover(ls: ProbLinterServer, params: HoverParams):
    """
    Return diagnostic messages for the current line as hover text.
    This enables `vim.lsp.buf.hover()` in Neovim to show linter errors.
    """
    document = ls.workspace.get_text_document(params.text_document.uri)

    if document.uri not in ls.diagnostics:
        await ls.lint_and_publish(document.uri)

    _, diagnostics = ls.diagnostics.get(document.uri, (None, []))

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
