from __future__ import annotations
from ldm.lib_config2.parsing_types import Structure, StructureComponentType
from ldm.source_tokenizer.tokenize import tokenize, TokenizerItems, TokenType
from ldm.ast.parsing_types import *
from ldm.errors.LDMError import error


def parse_expression(tokens: TokenIterator, items: ParsingItems):
    """
    TODO implement
    :param tokens: token iterator
    :param items: parsing items
    :return: Expression token
    """
    t, ind = next(tokens)
    val: str = t.type.value[0]

    if t.type == TokenType.Identifier:
        val = t.value

    if val in items.config_spec.initializer_formats:
        spec = items.config_spec.initializer_formats[val]
        val_type = spec.ref_type
    else:
        val_type = t.type.value[0]

    return t, val_type


def parse_structure(tokens: TokenIterator,
                    structure: Structure,
                    items: ParsingItems,
                    context: ParsingContext,
                    tokenizer_items: TokenizerItems) -> dict[str, Token]:
    structure_count = 0
    parsed_variables: dict[str, Token] = {}
    while structure_count < len(structure.component_defs) and not tokens.done():
        s = structure.component_defs[structure_count]

        if s.component_type == StructureComponentType.Variable:
            if s.value not in structure.component_specs:
                raise RuntimeError(f"structure component {s.value} not found")
            var = structure.component_specs[s.value]

            if var.base == 'typename':
                # get typename, check primitive types
                tn, _ = next(tokens)
                if tn.value not in items.config_spec.primitive_types:
                    raise RuntimeError(f'{tn} not a type on line {tn.line}')
                parsed_variables[var.name] = tn
                structure_count += 1

            elif var.base == 'name':
                var_type = 'existing-global'
                if 'type' in var.other:
                    var_type = var.other['type']

                varname, _ = next(tokens)

                if var_type == 'existing-global':
                    if not context.has_global(varname.value):
                        raise RuntimeError(f'{varname} does not exist at line {varname.line}')
                elif var_type == 'existing-local':
                    if not context.has_local(varname.value):
                        raise RuntimeError(f'{varname} does not exist at line {varname.line}')
                elif var_type == 'new-global':
                    if context.has_global(varname.value):
                        raise RuntimeError(f'{varname} already exists at line {varname.line}')
                elif var_type == 'new-local':
                    if context.has_local(varname.value):
                        raise RuntimeError(f'{varname} already exists at line {varname.line}')
                elif var_type != 'any':
                    raise RuntimeError(f'make-variable type "{var_type}" not recognized')

                parsed_variables[var.name] = varname
                structure_count += 1

            elif var.base == 'expression':
                expr, var_type = parse_expression(tokens, items)

                parsed_variables[var.name] = ExpressionToken(expr, var_type)
                structure_count += 1

            else:
                raise RuntimeError(f'base {var.base} not recognized')

        elif s.component_type == StructureComponentType.String:
            string_tokens = tokenize(s.value, tokenizer_items)
            for token in string_tokens:
                tn, _ = next(tokens)
                if tn.value != token.value:
                    raise RuntimeError(f'Expected {token.value}, got {tn.value} at line {tn.line}')
            structure_count += 1

        elif s.component_type == StructureComponentType.Command:
            pass

        elif s.component_type == StructureComponentType.EndCommand:
            pass

    return parsed_variables


def parse(tokens: list[Token], parsing_items: ParsingItems, tokenizer_items: TokenizerItems):

    context = ParsingContext()
    iterator = TokenIterator(tokens)

    mvs = parsing_items.config_spec.make_variables
    mv = mvs[list(mvs.keys())[0]]
    mv_structure = mv.structure

    ast_nodes = []
    while not iterator.done():
        node = parse_structure(iterator, mv_structure, parsing_items, context, tokenizer_items)
        mv = MakeVariableInstance('standard', node)
        ast_nodes.append(mv)

    return ast_nodes
