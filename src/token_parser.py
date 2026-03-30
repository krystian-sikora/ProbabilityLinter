from html.parser import HTMLParser
from logging import debug

from src.tokenizer import Token

config = {
    "statement": {
        "html-tag-name": "statement",
        "params": ["s"],
        "self-closing": False
    },
    "constraint": {
        "html-tag-name": "constraint",
        "params": ["c"],
        "self-closing": True
    },
    "probability": {
        "html-tag-name": "probability",
        "params": ["p"],
        "self-closing": False
    }
}


class InlineHTMLParser(HTMLParser):
    """Pomocniczy parser do wyciąganania tagów i ich atrybutów z html_inline"""

    def __init__(self):
        super().__init__()
        self.extracted_tag = None
        self.extracted_attrs = {}
        self.is_closing = False

    def handle_starttag(self, tag, attrs):
        self.extracted_tag = tag
        self.extracted_attrs = dict(attrs)

    def handle_endtag(self, tag):
        self.extracted_tag = tag
        self.is_closing = True


class TokenParser:
    """
    Class to parse the list of tokens and extract relevant information.
    """

    def __init__(self):
        pass

    def parse(self, tokens: list[Token]) -> None:
        """
        Method to parse the list of tokens and extract relevant information.
        :param tokens: list of Token objects
        :return: None
        """

        for token in tokens:
            self._parse(token)

    def _parse(self, token: Token) -> None:
        """
        Helper method to parse a single token.
        :param token: a Token object
        :return: None
        """

        debug(token)
