from __future__ import annotations
from ldm.source_tokenizer.tokenize import TokenizerItems
from ldm.ast.parsing_types import *
from ldm.ast.structure_parser import StructureParser


def __create_structure_list(self, token: Token) -> list[Keyw]:
    if token.type != TokenType.Operator:
        return []

    possible_operators = []

    has_left = False

    if self.workingOperator is not None and \
            len(self.workingOperator.operands) == self.workingOperator.operator.num_variables:
        has_left = True

    elif not self.workingOperator and len(self.stack) > 0:
        has_left = True

    for op in self.items.config_spec.operators.values():
        if op.trigger == token.value:
            if not has_left and (
                    op.operator_type == OperatorType.UNARY_RIGHT or
                    op.operator_type == OperatorType.INTERNAL
            ):
                possible_operators.append(OperatorInstance(op, [], '', None, token))
            elif has_left and (
                    op.operator_type == OperatorType.UNARY_LEFT or
                    op.operator_type == OperatorType.BINARY
            ):
                possible_operators.append(OperatorInstance(op, [], '', None, token))

    return possible_operators


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
