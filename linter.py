import logging
from argparse import ArgumentParser
from logging import basicConfig

from token_parser import TokenParser
from tokenizer import Tokenizer

basicConfig(level="DEBUG", format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("markdown_it").setLevel(logging.WARNING)

arg_parser = ArgumentParser()
arg_parser.add_argument("-f", "--file", dest="file_path",
                        help="markdown file to lint", metavar="FILE", required=True)

args = arg_parser.parse_args()

if __name__ == "__main__":
    tokenizer = Tokenizer()
    tokens = tokenizer.tokenize(args.file_path)
    parser = TokenParser()
    parser.parse(tokens)
