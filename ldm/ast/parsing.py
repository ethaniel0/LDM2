from __future__ import annotations
from ldm.source_tokenizer.tokenize import TokenizerItems
from ldm.source_tokenizer.tokenizer_types import TokenType
from ldm.ast.parsing_types import *
from ldm.ast.structure_parser import StructureParser, ExpressionParser, StructureComponentType


def __create_structure_list(tokens: TokenIterator, parsing_items: ParsingItems, context: ParsingContext) -> list[KeywordInstance | MakeVariableInstance]:
    token = tokens.peek()

    possible_keywords: list[KeywordInstance | MakeVariableInstance] = []
    for kw in parsing_items.config_spec.keywords.values():
        if kw.trigger == token.value:
            kwi = KeywordInstance(kw, [], token)
            possible_keywords.append(kwi)

    for mv in parsing_items.config_spec.make_variables.values():
        first_component = mv.structure.component_defs[0]
        if first_component.component_type == StructureComponentType.String and first_component.value == token.value:
            mvi = MakeVariableInstance(mv, {})
            possible_keywords.append(mvi)

        elif first_component.component_type == StructureComponentType.Variable:
            spec_component = mv.structure.component_specs[first_component.value]

            if spec_component.base == 'expression':
                exp = ExpressionParser(parsing_items)
                test_iterator = TokenIterator(tokens.tokens[tokens.index:])
                exp.set_tokens_and_context(test_iterator, context)
                result = exp.parse_until_full_tree()
                if result is not None:
                    component_dict = {spec_component.name: result}
                    mvi = MakeVariableInstance(mv, component_dict)
                    possible_keywords.append(mvi)

            elif spec_component.base == 'typename':
                if token.value in parsing_items.config_spec.primitive_types:
                    component_dict = {spec_component.name: TypeSpec(token.value, 0, [])}
                    mvi = MakeVariableInstance(mv, component_dict)
                    possible_keywords.append(mvi)

            elif spec_component.base == 'name':
                if context.has_global(token.value):
                    component_dict = {spec_component.name: context.get_global(token.value)}
                    mvi = MakeVariableInstance(mv, component_dict)
                    possible_keywords.append(mvi)

            else:
                raise ValueError(f"Unknown base {spec_component.base} for component {spec_component.name}")

    return possible_keywords


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

        possible_structures = __create_structure_list(iterator, parsing_items, context)
        for structure in possible_structures:
            if isinstance(structure, KeywordInstance):
                node = sp.parse(iterator, structure.keyword.structure, context)
                structure.components = node
                ast_nodes.append(structure)

            elif isinstance(structure, MakeVariableInstance):
                node = sp.parse(iterator, structure.mv.structure, context)
                structure.components = node
                ast_nodes.append(structure)

    return ast_nodes
