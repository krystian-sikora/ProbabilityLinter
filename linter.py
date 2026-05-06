import logging
from argparse import ArgumentParser, Namespace
from logging import basicConfig
from typing import List

import lsp
from src.token_parser import lint, LintError
from src.semantic_parser import lint_semantic
from src.tokenizer import tokenize

logging.getLogger("markdown_it").setLevel(logging.WARNING)
log_format = "%(asctime)s - %(levelname)s - %(message)s"


def parse_args() -> Namespace:
    """
    Parses command-line arguments to determine the mode of operation (LSP or CLI)
    and the file path for linting if in CLI mode.
    :return: Namespace object containing the parsed arguments
    """
    arg_parser = ArgumentParser()

    arg_parser.add_argument("-debug", dest="debug", help="show debug logs", action="store_true")
    arg_parser.add_argument("-lsp", dest="lsp", help="use lsp mode", action="store_true")
    arg_parser.add_argument("-f", dest="file_path", help="markdown file to lint",
                            metavar="FILE", type=str)
    _args = arg_parser.parse_args()

    if not _args.lsp and not _args.file_path:
        arg_parser.error("Either -lsp or -f FILE must be specified for CLI mode.")

    if _args.lsp and _args.file_path:
        arg_parser.error("Cannot specify both -lsp and -f FILE. Choose one mode of operation.")

    return _args


def to_gcc(path: str, err: List[LintError]) -> List[str]:
    """
    Converts an array of LintErrors into an array of GCC formatted strings.
    :param path: the file path to include in the error messages
    :param err: the array of LintErrors
    :return: array of GCC formatted strings
    """
    return [f"{path}:{e.line}:{e.col}: {e.severity}: {e.message}" for e in err]


def lint_source(source: str, path: str = "<string>") -> list[str]:
    """
    Lints a raw source string and returns GCC-formatted error strings.
    Useful for testing and for CLI file mode.
    """
    tokens = tokenize(source)
    errors = lint(tokens)
    errors.extend(lint_semantic(tokens))
    return to_gcc(path, errors)


if __name__ == "__main__":
    args = parse_args()

    if args.debug:
        basicConfig(level="DEBUG", format=log_format)

    if args.lsp:
        lsp.start_server()
    else:
        source = open(args.file_path).read()
        gcc_errors = lint_source(source, args.file_path)

        for gcc_error in gcc_errors:
            print(gcc_error)
