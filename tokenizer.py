from markdown_it import MarkdownIt
from markdown_it.token import Token


class Tokenizer:
    """
    This class is used to tokenize the text of the Markdown file.
    """

    def __init__(self):
        self.markdown = MarkdownIt("commonmark", {"html": True})

    def tokenize(self, file_path: str) -> list[Token]:
        """
        Method to tokenize the text of the Markdown file.
        :param file_path: path to the Markdown file to be tokenized.
        :return: list of Token objects
        """
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()

        return self.markdown.parse(text)
