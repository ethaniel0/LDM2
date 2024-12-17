from __future__ import annotations

from typing import Any

from ldm.source_tokenizer.tokenize import Token, TokenizerItems, Tokenizer
from ldm.ast.parsing_types import (TokenIterator, ParsingItems, ParsingContext,
                                   OperatorInstance, ValueToken,
                                   StructuredObjectInstance, NameInstance, TypenameInstance, SOInstanceItem)
from ldm.lib_config2.parsing_types import Structure, StructureComponentType, StructureComponent, TypeSpec, ComponentType
from ldm.ast.expression_parser import ExpressionParser


def to_typespec(token: Token) -> TypeSpec:
    return TypeSpec(token.value, 0, [])


class StructureParser:
    def __init__(self, items: ParsingItems, tokenizer_items: TokenizerItems):
        self.items = items
        self.tokenizer_items = tokenizer_items
        self.expression_parser = ExpressionParser(items)

    def __handle_typename(self, tokens: TokenIterator):
        # get typename, check primitive types
        tn, _ = next(tokens)
        if tn.value not in self.items.config_spec.primitive_types:
            raise RuntimeError(f'{tn} not a type on line {tn.line}')
        return TypenameInstance(ComponentType.TYPENAME, TypeSpec(tn.value, 0, []))

    def __handle_name(self, comp: StructureComponent, structure: Structure, tokens: TokenIterator, context: ParsingContext):
        var = structure.component_specs[comp.value]

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

        return NameInstance(ComponentType.NAME, varname.value)

    def __handle_expression(self, tokens: TokenIterator, context: ParsingContext, var_index: int, structure: Structure):
        until = ""
        if var_index < len(structure.component_defs) - 1:
            next_comp = structure.component_defs[var_index + 1]
            if next_comp.component_type == StructureComponentType.String:
                until = next_comp.value

        self.expression_parser.set_tokens_and_context(tokens, context)
        expr = self.expression_parser.parse(until)

        return SOInstanceItem(ComponentType.EXPRESSION, expr)

    def __handle_expressions(self, tokens: TokenIterator, context: ParsingContext, var_index: int, structure: Structure):
        comp = structure.component_defs[var_index]
        var = structure.component_specs[comp.value]

        local = False
        if 'scope' in var.other:
            if var.other['scope'] == 'local':
                local = True
            elif var.other['scope'] != 'global':
                raise RuntimeError(f"Unknown scope {var.other['scope']} for block")

        if local:
            block_context = ParsingContext(context)
            block_context.parent = context
        else:
            block_context = context

        sp = StructureParser(self.items, self.tokenizer_items)
        if len(structure.component_defs) <= var_index + 1:
            raise RuntimeError(f'Expressions variable in structure must have a following string')
        next_comp_def = structure.component_defs[var_index + 1]
        if next_comp_def.component_type != StructureComponentType.String:
            raise NotImplementedError('Variable after an expressions structure component not implemented')
        result = sp.parse(tokens, block_context, until=next_comp_def.value)
        if result is None:
            raise RuntimeError(f'Could not parse expressions')
        return SOInstanceItem(ComponentType.EXPRESSIONS, result)

    def __handle_variable(self, var_index: int, structure: Structure, tokens: TokenIterator, context: ParsingContext):
        comp = structure.component_defs[var_index]
        if comp.value not in structure.component_specs:
            raise RuntimeError(f"structure component {comp.value} not found")
        var = structure.component_specs[comp.value]

        if var.base == ComponentType.TYPENAME:
            return var.name, self.__handle_typename(tokens)

        elif var.base == ComponentType.NAME:
            return var.name, self.__handle_name(comp, structure, tokens, context)

        elif var.base == ComponentType.EXPRESSION:
            return var.name, self.__handle_expression(tokens, context, var_index, structure)

        elif var.base == ComponentType.EXPRESSIONS:
            return var.name, self.__handle_expressions(tokens, context, var_index, structure)

        elif var.base == ComponentType.REPEATED_ELEMENT:
            # create structure component and use that
            new_stucture = Structure(
                var.other['components'],
                comp.inner_structure
            )
            separator = comp.inner_fields['separator']

            repeat_end = structure.component_defs[var_index + 1]
            if repeat_end.component_type != StructureComponentType.String:
                raise RuntimeError(f'Variables after repeated structures are not yet supported.')

            sp = StructureParser(self.items, self.tokenizer_items)

            elements = []
            while tokens.peek().value != repeat_end.value:
                result = sp.__parse_single_structure(tokens, new_stucture, context)
                if tokens.peek().value != separator and tokens.peek().value != repeat_end.value:
                    raise RuntimeError(f"Unable to parse component structure at {tokens.peek()}")
                if tokens.peek().value == separator:
                    next(tokens)
                elements.append(result)

            return var.name, SOInstanceItem(ComponentType.REPEATED_ELEMENT, elements)

        elif var.base == ComponentType.STRUCTURE:
            next_structure_name = var.other['structure']
            next_structure = self.items.config_spec.structured_objects[next_structure_name]
            node = self.__parse_single_structure(tokens, next_structure.structure, context)
            return var.name, SOInstanceItem(ComponentType.STRUCTURE, node)

        else:
            raise RuntimeError(f'base {var.base} not recognized')

    def __parse_single_structure(self, tokens: TokenIterator, structure: Structure, context: ParsingContext):
        structure_count = 0
        parsed_variables: dict[str, Token] = {}

        while structure_count < len(structure.component_defs) and not tokens.done():
            s = structure.component_defs[structure_count]

            if s.component_type == StructureComponentType.Variable:
                n, v = self.__handle_variable(structure_count, structure, tokens, context)
                parsed_variables[n] = v
                structure_count += 1

            elif s.component_type == StructureComponentType.String:
                string_tokens = Tokenizer(self.tokenizer_items).tokenize(s.value)
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

    def __create_structure_list(self, tokens: TokenIterator, context: ParsingContext) -> list[StructuredObjectInstance]:
        token = tokens.peek()

        possible_structures: list[StructuredObjectInstance] = []

        for so in self.items.config_spec.structured_objects.values():
            if len(so.structure.component_defs) == 0 or so.dependent:
                continue
            first_component = so.structure.component_defs[0]
            if first_component.component_type == StructureComponentType.String and first_component.value == token.value:
                soi = StructuredObjectInstance(so, {})
                possible_structures.append(soi)

            elif first_component.component_type == StructureComponentType.Variable:
                spec_component = so.structure.component_specs[first_component.value]

                if spec_component.base == ComponentType.EXPRESSION:
                    exp = ExpressionParser(self.items)
                    test_iterator = TokenIterator(tokens.tokens[tokens.index:])
                    exp.set_tokens_and_context(test_iterator, context)
                    result = exp.parse_until_full_tree()
                    if result is not None:
                        component_dict = {spec_component.name: result}
                        soi = StructuredObjectInstance(so, component_dict)
                        possible_structures.append(soi)

                elif spec_component.base == ComponentType.TYPENAME:
                    if token.value in self.items.config_spec.primitive_types:
                        component_dict = {spec_component.name: token}
                        soi = StructuredObjectInstance(so, component_dict)
                        possible_structures.append(soi)

                elif spec_component.base == ComponentType.NAME:
                    if context.has_global(token.value):
                        component_dict = {spec_component.name: context.get_global(token.value)}
                        soi = StructuredObjectInstance(so, component_dict)
                        possible_structures.append(soi)

                else:
                    raise ValueError(f"Unknown base {spec_component.base} for component {spec_component.name}")

        return possible_structures

    def parse(self, tokens: TokenIterator, context: ParsingContext, until="") -> list[StructuredObjectInstance | OperatorInstance | ValueToken]:

        ast_nodes = []
        while not tokens.done():
            if until != "" and tokens.peek().value == until:
                break

            possible_structures = self.__create_structure_list(tokens, context)

            if len(possible_structures) == 0:
                exp = ExpressionParser(self.items)
                exp.set_tokens_and_context(tokens, context)
                result = exp.parse()
                ast_nodes.append(result)
                continue

            working_structures = []
            token_nums = []

            cur_index = tokens.index

            errors_found = []

            for structure in possible_structures:
                try:
                    node = self.__parse_single_structure(tokens, structure.so.structure, context)
                    structure.components = node
                    working_structures.append((structure, node))
                    token_nums.append(tokens.index)
                except RuntimeError as e:
                    errors_found.append(f"{structure.so.name}: {e}")
                    pass

                tokens.goto(cur_index)

            if len(working_structures) == 0:
                if len(errors_found) == 1:
                    raise RuntimeError(errors_found[0])

                total_error = "Possible Structure Errors:"
                for e in errors_found:
                    total_error += f"\n\t{e}"
                raise RuntimeError(total_error)

            max_components = 0
            max_structure: None | tuple[StructuredObjectInstance, dict[str, Any]] = None
            max_index = 0
            for i in range(len(working_structures)):
                if len(working_structures[i][1]) > max_components:
                    max_components = len(working_structures[i][1])
                    max_structure = working_structures[i]
                    max_index = token_nums[i]

            ast_nodes.append(max_structure[0])
            tokens.goto(max_index)
            if max_structure[0].so.value_type:
                name = max_structure[0].so.value_name
                if name.startswith('$'):
                    name = max_structure[1][name[1:]].value
                so_type = max_structure[0].so.value_type
                if so_type.name.startswith('$'):
                    so_type = max_structure[1][so_type.name[1:]].value

                context.variables[name] = so_type

        return ast_nodes
