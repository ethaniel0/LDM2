from __future__ import annotations
from ldm.source_tokenizer.tokenize import TokenizerItems
from ldm.ast.parsing_types import *
from ldm.ast.structure_parser import StructureParser


def parse(tokens: list[Token], parsing_items: ParsingItems, tokenizer_items: TokenizerItems):
    # create context to be used when parsing
    context = ParsingContext()
    iterator = TokenIterator(tokens)

    # while simplified, only ever use the main make_variable structure
    mvs = parsing_items.config_spec.make_variables
    mv = mvs[list(mvs.keys())[0]]
    mv_structure = mv.structure

    # create structure parser
    sp = StructureParser(parsing_items, tokenizer_items)

    # parse all tokens into asts
    ast_nodes = []
    while not iterator.done():
        node = sp.parse(iterator, mv_structure, context)
        mv = MakeVariableInstance('standard', node)
        ast_nodes.append(mv)

    return ast_nodes
