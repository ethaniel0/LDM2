from __future__ import annotations
from ldm.source_tokenizer.tokenize import Token, TokenizerItems, Tokenizer
from ldm.ast.parsing_types import (TokenIterator, ParsingItems, ParsingContext,
                                   OperatorInstance, ValueToken, BlockInstance, KeywordInstance, MakeVariableInstance)
from ldm.lib_config2.parsing_types import Structure, StructureComponentType, StructureComponent, TypeSpec
from ldm.ast.expression_parser import ExpressionParser


def to_typespec(token: Token) -> TypeSpec:
    return TypeSpec(token.value, 0, [])

class StructureParser:
    def __init__(self, items: ParsingItems, tokenizer_items: TokenizerItems):
        self.items = items
        self.tokenizer_items = tokenizer_items

        self.structure_count = 0
        self.parsed_variables: dict[str, Token | ValueToken | OperatorInstance | BlockInstance] = {}
        self.context: ParsingContext = ParsingContext()
        self.tokens: TokenIterator = TokenIterator([])

        self.expression_parser = ExpressionParser(items)

    def __handle_typename(self, comp: StructureComponent, structure: Structure):
        var = structure.component_specs[comp.value]
        # get typename, check primitive types
        tn, _ = next(self.tokens)
        if tn.value not in self.items.config_spec.primitive_types:
            raise RuntimeError(f'{tn} not a type on line {tn.line}')
        self.parsed_variables[var.name] = tn
        self.structure_count += 1

    def __handle_name(self, comp: StructureComponent, structure: Structure):
        var = structure.component_specs[comp.value]

        var_type = 'existing-global'
        if 'type' in var.other:
            var_type = var.other['type']

        varname, _ = next(self.tokens)

        if var_type == 'existing-global':
            if not self.context.has_global(varname.value):
                raise RuntimeError(f'{varname} does not exist at line {varname.line}')
        elif var_type == 'existing-local':
            if not self.context.has_local(varname.value):
                raise RuntimeError(f'{varname} does not exist at line {varname.line}')
        elif var_type == 'new-global':
            if self.context.has_global(varname.value):
                raise RuntimeError(f'{varname} already exists at line {varname.line}')
        elif var_type == 'new-local':
            if self.context.has_local(varname.value):
                raise RuntimeError(f'{varname} already exists at line {varname.line}')
        elif var_type != 'any':
            raise RuntimeError(f'make-variable type "{var_type}" not recognized')

        self.parsed_variables[var.name] = varname
        self.structure_count += 1

    def __handle_expression(self, var_index: int, structure: Structure):
        comp = structure.component_defs[var_index]

        var = structure.component_specs[comp.value]
        until = ""
        if var_index < len(structure.component_defs) - 1:
            next_comp = structure.component_defs[var_index + 1]
            if next_comp.component_type == StructureComponentType.String:
                until = next_comp.value

        self.expression_parser.set_tokens_and_context(self.tokens, self.context)
        expr = self.expression_parser.parse(until)

        self.parsed_variables[var.name] = expr
        self.structure_count += 1

    def __get_valid_blocks(self, block: StructureComponent) -> list[BlockInstance]:
        blocks = []
        for b in self.items.config_spec.block_structures.values():
            if b.structure.component_defs[0].component_type == StructureComponentType.String and \
                    b.structure.component_defs[0].value == self.tokens.peek().value:
                blocks.append(BlockInstance(b, {}, self.tokens.peek()))
            if b.structure.component_defs[0].component_type == StructureComponentType.Variable:
                raise NotImplementedError('Variable block structures not implemented')
        return blocks

    def __handle_block(self, block: StructureComponent):
        blocks = self.__get_valid_blocks(block)

        cur_index = self.tokens.index

        if len(blocks) == 0:
            raise RuntimeError(f'Block not found at for structure on line {self.tokens.peek().line}')

        working_blocks = []
        ending_indices = []

        for b in blocks:
            components_parsed = 0
            components_needed = len(b.block.structure.component_defs)

            for i in range(len(b.block.structure.component_defs)):
                comp = b.block.structure.component_defs[i]
                if comp.component_type == StructureComponentType.Variable:
                    comp_type = b.block.structure.component_specs[comp.value].base
                    if comp_type == 'block':
                        sp = StructureParser(self.items, self.tokenizer_items)

                        next_comp = b.block.structure.component_defs[i + 1]
                        if next_comp.component_type != StructureComponentType.String:
                            raise RuntimeError(f'config block must have an ending character')

                        result = sp.parse(self.tokens, self.context, until=next_comp.value)
                        if result is None:
                            break
                        b.components[comp.value] = result
                    else:
                        raise NotImplementedError('Variable block structures not implemented')
                elif comp.component_type == StructureComponentType.String:
                    if self.tokens.peek().value != comp.value:
                        break
                    next(self.tokens)
                components_parsed += 1

            if components_parsed != components_needed:
                break

            working_blocks.append(b)
            ending_indices.append(self.tokens.index)

            self.tokens.goto(cur_index + 1)

        if len(working_blocks) == 0:
            block_token = self.tokens.peek()
            raise RuntimeError(f'Could not parse block {block_token} at line {block_token.line}')

        block_choice: None | BlockInstance = None
        if len(working_blocks) == 1:
            block_choice = working_blocks[0]
            self.tokens.goto(ending_indices[0])
        else:
            max_components = 0
            for i in range(len(working_blocks)):
                if len(working_blocks[i].components) > max_components:
                    max_components = len(working_blocks[i].components)
                    block_choice = working_blocks[i]
                    self.tokens.goto(ending_indices[i])

        return block_choice

    def __handle_variable(self, var_index: int, structure: Structure):
        comp = structure.component_defs[var_index]
        if comp.value not in structure.component_specs:
            raise RuntimeError(f"structure component {comp.value} not found")
        var = structure.component_specs[comp.value]

        if var.base == 'typename':
            self.__handle_typename(comp, structure)

        elif var.base == 'name':
            self.__handle_name(comp, structure)

        elif var.base == 'expression':
            self.__handle_expression(var_index, structure)

        elif var.base == 'block':
            block = self.__handle_block(comp)
            if block is not None:
                self.parsed_variables[var.name] = block
                self.structure_count += 1

        else:
            raise RuntimeError(f'base {var.base} not recognized')

    def __parse_single_structure(self, tokens: TokenIterator, structure: Structure, context: ParsingContext):
        self.structure_count = 0
        self.parsed_variables: dict[str, Token] = {}
        self.context = context
        self.tokens = tokens

        while self.structure_count < len(structure.component_defs) and not tokens.done():
            s = structure.component_defs[self.structure_count]

            if s.component_type == StructureComponentType.Variable:
                self.__handle_variable(self.structure_count, structure)

            elif s.component_type == StructureComponentType.String:
                string_tokens = Tokenizer(self.tokenizer_items).tokenize(s.value)
                for token in string_tokens:
                    tn, _ = next(tokens)
                    if tn.value != token.value:
                        raise RuntimeError(f'Expected {token.value}, got {tn.value} at line {tn.line}')
                self.structure_count += 1

            elif s.component_type == StructureComponentType.Command:
                pass

            elif s.component_type == StructureComponentType.EndCommand:
                pass

        return self.parsed_variables

    def __create_structure_list(self, tokens: TokenIterator, context: ParsingContext) -> list[KeywordInstance | MakeVariableInstance]:
        token = tokens.peek()

        possible_keywords: list[KeywordInstance | MakeVariableInstance] = []
        for kw in self.items.config_spec.keywords.values():
            if kw.trigger == token.value:
                kwi = KeywordInstance(kw, {}, token)
                possible_keywords.append(kwi)

        for mv in self.items.config_spec.make_variables.values():
            first_component = mv.structure.component_defs[0]
            if first_component.component_type == StructureComponentType.String and first_component.value == token.value:
                mvi = MakeVariableInstance(mv, {})
                possible_keywords.append(mvi)

            elif first_component.component_type == StructureComponentType.Variable:
                spec_component = mv.structure.component_specs[first_component.value]

                if spec_component.base == 'expression':
                    exp = ExpressionParser(self.items)
                    test_iterator = TokenIterator(tokens.tokens[tokens.index:])
                    exp.set_tokens_and_context(test_iterator, context)
                    result = exp.parse_until_full_tree()
                    if result is not None:
                        component_dict = {spec_component.name: result}
                        mvi = MakeVariableInstance(mv, component_dict)
                        possible_keywords.append(mvi)

                elif spec_component.base == 'typename':
                    if token.value in self.items.config_spec.primitive_types:
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

    def parse(self, tokens: TokenIterator, context: ParsingContext, until="") -> list[KeywordInstance | MakeVariableInstance | OperatorInstance | ValueToken]:
        self.structure_count = 0
        self.parsed_variables: dict[str, Token] = {}
        self.context = context
        self.tokens = tokens

        ast_nodes = []
        while not tokens.done():
            if until != "" and tokens.peek().value == until:
                break

            possible_structures = self.__create_structure_list(tokens, context)

            if len(possible_structures) == 0:
                # evaluate as expression
                exp = ExpressionParser(self.items)
                exp.set_tokens_and_context(tokens, context)
                result = exp.parse()
                ast_nodes.append(result)
                continue

            for structure in possible_structures:
                if isinstance(structure, KeywordInstance):
                    node = self.__parse_single_structure(tokens, structure.keyword.structure, context)
                    structure.components = node
                    ast_nodes.append(structure)

                elif isinstance(structure, MakeVariableInstance):
                    node = self.__parse_single_structure(tokens, structure.mv.structure, context)
                    structure.components = node
                    ast_nodes.append(structure)
                    context.variables[structure.components['varname'].value] = to_typespec(structure.components['typename'])

        return ast_nodes
