from lsprotocol import types
from lsprotocol.types import (
    TEXT_DOCUMENT_DID_OPEN, TEXT_DOCUMENT_DID_CHANGE,
    Diagnostic, DiagnosticSeverity, Position, Range,
    DidOpenTextDocumentParams,
)
from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument

from src.token_parser import lint
from src.semantic_parser import lint_semantic
from src.tokenizer import tokenize


class ProbLinterServer(LanguageServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostics = {}

    def make_diagnostics(self, document: TextDocument) -> None:
        diagnostics = []
        tokens = tokenize(document.source)

        all_errors = lint(tokens)
        all_errors.extend(lint_semantic(tokens))

        for error in all_errors:
            severity = {
                "error": DiagnosticSeverity.Error,
                "warning": DiagnosticSeverity.Warning,
                "info": DiagnosticSeverity.Information,
            }.get(error.severity, DiagnosticSeverity.Error)
            diagnostics.append(Diagnostic(
                range=Range(
                    start=Position(line=error.line - 1, character=error.col - 1),
                    end=Position(line=error.line - 1, character=error.col - 1 + error.offset),
                ),
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


def start_server():
    server.start_io()


if __name__ == "__main__":
    start_server()
