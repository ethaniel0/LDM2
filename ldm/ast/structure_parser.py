from __future__ import annotations
from ldm.source_tokenizer.tokenize import Token, TokenizerItems, Tokenizer, TokenType
from ldm.ast.parsing_types import (TokenIterator, ParsingItems, ParsingContext,
                                   OperatorInstance, ValueToken)
from ldm.lib_config2.parsing_types import Structure, StructureComponentType, StructureComponent, TypeSpec


def create_operator_list(token: Token, items: ParsingItems) -> list[OperatorInstance]:
    if token.type != TokenType.Operator:
        return []

    possible_operators = []

    for op in items.config_spec.operators.values():
        if op.trigger == token.value:
            possible_operators.append(OperatorInstance(op, [], '', None))

    return possible_operators


class ExpressionParser:
    def __init__(self, items: ParsingItems):
        self.items = items
        self.stack = []
        self.workingOperator: ValueToken | OperatorInstance | None = None
        self.tokens = TokenIterator
        self.parsing_context = ParsingContext()

    def __parse_operator_structure(self, op_token: Token):
        ops = create_operator_list(op_token, self.items)
        if len(ops) == 0:
            raise RuntimeError(f'Operator {op_token} not found at line {op_token.line}')

        # need to check operator structure to determine which operator to use








    def __parse_value(self, token: Token) -> ValueToken:
        init_formats = self.items.config_spec.initializer_formats

        if token.type == TokenType.Integer:
            if '$int' in init_formats:
                ts = TypeSpec(init_formats['$int'].ref_type, 0, [])
                return ValueToken(token, ts, None)
            raise RuntimeError(f'No initializer format for int')

        if token.type == TokenType.Float:
            if '$float' in init_formats:
                ts = TypeSpec(init_formats['$float'].ref_type, 0, [])
                return ValueToken(token, ts, None)
            raise RuntimeError(f'No initializer format for float')

        if token.type == TokenType.String:
            if '$string' in init_formats:
                ts = TypeSpec(init_formats['$string'].ref_type, 0, [])
                return ValueToken(token, ts, None)
            raise RuntimeError(f'No initializer format for string')

        if token.type == TokenType.ValueKeyword:
            if token.value in init_formats:
                ts = TypeSpec(init_formats[token.value].ref_type, 0, [])
                return ValueToken(token, ts, None)
            raise RuntimeError(f'No initializer format for {token.value}')

        if token.type == TokenType.Identifier:
            v = self.parsing_context.get_global(token.value)
            if v is None:
                raise RuntimeError(f'{token} not found at line {token.line}')
            return ValueToken(token, v, None)

    def parse(self, tokens: TokenIterator, context: ParsingContext) -> ValueToken | OperatorInstance:
        self.parsing_context = context
        self.workingOperator = None

        for t, i in tokens:
            if t.type == TokenType.Operator:
                self.__parse_operator_structure(t)
            else:
                val = self.__parse_value(t)
                self.stack.append(val)

        return self.stack[0]


class StructureParser:
    def __init__(self, items: ParsingItems, tokenizer_items: TokenizerItems):
        self.items = items
        self.tokenizer_items = tokenizer_items

        self.structure_count = 0
        self.parsed_variables: dict[str, Token | ValueToken | OperatorInstance] = {}
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

    def __handle_expression(self, comp: StructureComponent, structure: Structure):
        var = structure.component_specs[comp.value]

        expr = self.expression_parser.parse(self.tokens, self.context)

        self.parsed_variables[var.name] = expr
        self.structure_count += 1

    def __handle_variable(self, comp: StructureComponent, structure: Structure):
        if comp.value not in structure.component_specs:
            raise RuntimeError(f"structure component {comp.value} not found")
        var = structure.component_specs[comp.value]

        if var.base == 'typename':
            self.__handle_typename(comp, structure)

        elif var.base == 'name':
            self.__handle_name(comp, structure)

        elif var.base == 'expression':
            self.__handle_expression(comp, structure)

        else:
            raise RuntimeError(f'base {var.base} not recognized')

    def parse(self, tokens: TokenIterator, structure: Structure, context: ParsingContext) -> dict[str, Token]:
        self.structure_count = 0
        self.parsed_variables: dict[str, Token] = {}
        self.context = context
        self.tokens = tokens

        while self.structure_count < len(structure.component_defs) and not tokens.done():
            s = structure.component_defs[self.structure_count]

            if s.component_type == StructureComponentType.Variable:
                self.__handle_variable(s, structure)

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
