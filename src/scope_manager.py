"""
Detect probability block boundaries from <block /> anchor tags.

Contract:
- <block /> or <block id="name" /> starts a new probability system.
- Tags before the first <block /> belong to an implicit "default" block.
- Each block is validated independently by PiterInterface.
"""
from dataclasses import dataclass

from src.token_parser import attr_str
from src.tokenizer import Token

LINTER_CONTENT_TAGS = frozenset({"symbol", "constraint", "prob", "query"})


@dataclass
class ProbabilityBlock:
    """A group of related tags that form one probability system."""
    tokens: list[Token]
    block_id: str = "default"

    @property
    def symbols(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "symbol"]

    @property
    def constraints(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "constraint"]

    @property
    def probabilities(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "prob"]

    @property
    def queries(self) -> list[Token]:
        return [t for t in self.tokens if t.tag == "query"]


def _assign_block_id(raw_id, index: int) -> str:
    if raw_id:
        return raw_id
    return f"block-{index}"


def build_blocks(tokens: list[Token]) -> list[ProbabilityBlock]:
    """
    Split tokens into probability blocks using <block /> anchors.

    Block delimiter tags are not included in block token lists.
    Empty blocks (anchor with no following content tags) are omitted.
    """
    markers = sorted(
        (
            (token.offset, _assign_block_id(attr_str(token.attrs, "id") or None, i + 1), token)
            for i, token in enumerate(tokens)
            if token.tag == "block"
        ),
        key=lambda item: item[0],
    )
    content = [token for token in tokens if token.tag in LINTER_CONTENT_TAGS]

    if not content:
        return []

    if not markers:
        return [ProbabilityBlock(tokens=content, block_id="default")]

    blocks: list[ProbabilityBlock] = []
    first_offset = markers[0][0]

    default_tokens = [token for token in content if token.offset < first_offset]
    if default_tokens:
        blocks.append(ProbabilityBlock(tokens=default_tokens, block_id="default"))

    for i, (offset, block_id, _marker) in enumerate(markers):
        next_offset = markers[i + 1][0] if i + 1 < len(markers) else None
        block_tokens = [
            token for token in content
            if token.offset >= offset
            and (next_offset is None or token.offset < next_offset)
        ]
        if block_tokens:
            blocks.append(ProbabilityBlock(tokens=block_tokens, block_id=block_id))

    return blocks
