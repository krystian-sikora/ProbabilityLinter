from markdown_it.token import Token


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
            print(f"Token type: {token.type}, content: {token.content}")
            self._parse(token)

            if token.children is not None:
                for child in token.children:
                    self._parse(child)

    def _parse(self, token: Token) -> None:
        """
        Helper method to parse a single token.
        :param token: a Token object
        :return: None
        """
        print(f"Parsing token of type: {token.type}, content: {token.content}")
