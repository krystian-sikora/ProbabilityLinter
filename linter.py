import logging
import sys
from argparse import ArgumentParser, Namespace
from logging import basicConfig, debug
from typing import List, Sequence

import lsp
from src.lint_error import LintError
from src.pipeline import collect_errors
from src.strip_tags import strip_tags

logging.getLogger("markdown_it").setLevel(logging.WARNING)
log_format = "%(asctime)s - %(levelname)s - %(message)s"


def parse_args(argv: Sequence[str] | None = None) -> Namespace:
    """
    Parses command-line arguments to determine the mode of operation (LSP, lint, or strip).
    :return: Namespace object containing the parsed arguments
    """
    arg_parser = ArgumentParser()

    arg_parser.add_argument("-debug", dest="debug", help="show debug logs", action="store_true")
    arg_parser.add_argument("-lsp", dest="lsp", help="use lsp mode", action="store_true")
    arg_parser.add_argument("-f", dest="file_path", help="markdown file to lint or strip",
                            metavar="FILE", type=str)
    arg_parser.add_argument(
        "-strip", "--strip-tags", dest="strip_tags", action="store_true",
        help="remove prob-linter tags from -f and write cleaned Markdown to -o",
    )
    arg_parser.add_argument(
        "-o", dest="output_path", metavar="FILE", type=str,
        help="output file for -strip (cleaned Markdown without prob-linter tags)",
    )
    _args = arg_parser.parse_args(argv)

    if _args.strip_tags:
        if not _args.file_path or not _args.output_path:
            arg_parser.error("-strip requires both -f FILE and -o FILE.")
        if _args.lsp:
            arg_parser.error("Cannot use -strip with -lsp.")
    elif not _args.lsp and not _args.file_path:
        arg_parser.error("Either -lsp or -f FILE must be specified for CLI mode.")
    elif _args.lsp and _args.file_path:
        arg_parser.error("Cannot specify both -lsp and -f FILE. Choose one mode of operation.")

    return _args


def run_strip_tags(args: Namespace) -> None:
    """Read *args.file_path*, strip prob-linter tags, write to *args.output_path*."""
    with open(args.file_path, encoding="utf-8") as inp:
        source = inp.read()
    cleaned = strip_tags(source)
    with open(args.output_path, "w", encoding="utf-8", newline="") as out:
        out.write(cleaned)
    print(f"Wrote cleaned Markdown to {args.output_path}", file=sys.stderr)


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
    return to_gcc(path, collect_errors(source))


if __name__ == "__main__":
    args = parse_args()

    if args.debug:
        basicConfig(level="DEBUG", format=log_format)

    if args.lsp:
        debug("Starting in LSP mode")
        lsp.start_server()
    elif args.strip_tags:
        run_strip_tags(args)
    else:
        source = open(args.file_path, encoding="utf-8").read()
        gcc_errors = lint_source(source, args.file_path)

        for gcc_error in gcc_errors:
            print(gcc_error)
