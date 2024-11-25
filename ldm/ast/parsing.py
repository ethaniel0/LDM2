from __future__ import annotations
from ldm.source_tokenizer.tokenize import TokenizerItems
from ldm.ast.parsing_types import ParsingContext, TokenIterator, ParsingItems, Token
from ldm.ast.structure_parser import StructureParser


def parse(tokens: list[Token], parsing_items: ParsingItems, tokenizer_items: TokenizerItems):
    # create context to be used when parsing
    context = ParsingContext()
    iterator = TokenIterator(tokens)

    # create structure parser
    sp = StructureParser(parsing_items, tokenizer_items)
    return sp.parse(iterator, context)
