from __future__ import annotations
from ldm.source_tokenizer.tokenize import Token, TokenizerItems, Tokenizer, TokenType
from ldm.ast.parsing_types import (TokenIterator, ParsingItems, ParsingContext,
                                   OperatorInstance, ValueToken)
from ldm.lib_config2.parsing_types import (Structure, StructureComponentType, StructureComponent, TypeSpec,
                                           OperatorType)


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
        self.tokens = TokenIterator([])
        self.parsing_context = ParsingContext()

    def __create_operator_list(self, token: Token) -> list[OperatorInstance]:
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
                    possible_operators.append(OperatorInstance(op, [], '', None))
                elif has_left and (
                    op.operator_type == OperatorType.UNARY_LEFT or
                    op.operator_type == OperatorType.BINARY
                ):
                    possible_operators.append(OperatorInstance(op, [], '', None))

        return possible_operators

    def __parse_operator_structure(self, op_token: Token, op_index: int):
        ops = self.__create_operator_list(op_token)

        if len(ops) == 0:
            raise RuntimeError(f'Operator {op_token} not found at line {op_token.line}')

        working_ops = []
        ending_indices = []

        for op in ops:
            op_has_left = op.operator.operator_type in [OperatorType.UNARY_LEFT, OperatorType.BINARY]
            op_components = op.operator.structure.component_defs
            index = 0
            for i in op_components:
                index += 1
                if i.component_type != StructureComponentType.Variable:
                    break

            for i in range(index, len(op_components)):
                comp = op_components[i]
                if comp.component_type == StructureComponentType.Variable:
                    ep = ExpressionParser(self.items)
                    ep.set_tokens_and_context(self.tokens, self.parsing_context)
                    tree = ep.parse_until_full_tree()
                    if tree is None:
                        break

                    if i == len(op_components) - 1:
                        op.operands.append(tree)
                        continue

                    next_comp = op_components[i + 1]
                    if next_comp.component_type == StructureComponentType.String:
                        successful = True

                        while self.tokens.peek() and next_comp.value != self.tokens.peek().value:
                            new_tree = ep.parse_until_full_tree()
                            if new_tree is None:
                                successful = False
                                break
                            tree = new_tree

                        if successful:
                            op.operands.append(tree)
                        else:
                            break
                    else:
                        new_tree = ep.parse_until_full_tree()
                        while new_tree is not None:
                            tree = new_tree
                            new_tree = ep.parse_until_full_tree()

                        op.operands.append(tree)

                else:
                    if not self.tokens.peek() or comp.value != self.tokens.peek().value:
                        break
                    next(self.tokens)

            if op_has_left and len(op.operands) == op.operator.num_variables - 1:
                working_ops.append(op)
                ending_indices.append(self.tokens.current_index())
            elif not op_has_left and len(op.operands) == op.operator.num_variables:
                working_ops.append(op)
                ending_indices.append(self.tokens.current_index())

            self.tokens.goto(op_index+1)

        if len(working_ops) == 0:
            raise RuntimeError(f'Could not parse operator {op_token} at line {op_token.line}')

        op_choice = None
        if len(working_ops) == 1:
            op_choice = working_ops[0]
            self.tokens.goto(ending_indices[0])

        else:
            # choose operator with most components
            max_components = 0

            for i in range(len(working_ops)):
                if len(working_ops[i].operands) > max_components:
                    max_components = len(working_ops[i].operands)
                    op_choice = working_ops[i]
                    self.tokens.goto(ending_indices[i])



        left_component = op_choice.operator.structure.component_defs[0]
        has_left = left_component.component_type == StructureComponentType.Variable

        if self.workingOperator is None:
            if has_left:
                if len(self.stack) == 0:
                    raise RuntimeError(f'No left operand for operator {op_token} at line {op_token.line}')
                op_choice.operands.insert(0, self.stack.pop())
            self.workingOperator = op_choice
        else:
            if has_left:
                while op_choice.operator.precedence >= self.workingOperator.operator.precedence or \
                        self.workingOperator.operator.operator_type in [OperatorType.UNARY_LEFT, OperatorType.INTERNAL]:
                    if len(self.workingOperator.operands) != self.workingOperator.operator.num_variables:
                        raise RuntimeError(f'Operator {self.workingOperator.operator.name} not fully parsed')
                    if self.workingOperator.parse_parent is None:
                        op_choice.operands.insert(0, self.workingOperator)
                        self.workingOperator = op_choice
                        break
                    self.workingOperator = self.workingOperator.parse_parent

                if op_choice != self.workingOperator:
                    op_choice.operands.insert(0, self.workingOperator.operands.pop())
                    self.workingOperator.operands.append(op_choice)
                    op_choice.parse_parent = self.workingOperator

                self.workingOperator = op_choice

            else:
                raise RuntimeError(f'Unexpected operator {op_token} at line {op_token.line}')

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

    def set_tokens_and_context(self, tokens: TokenIterator, context: ParsingContext):
        self.tokens = tokens
        self.parsing_context = context

    def parse_until_full_tree(self) -> ValueToken | OperatorInstance | None:
        while not self.tokens.done():
            t, i = next(self.tokens)
            if t.type == TokenType.Operator:
                try:
                    self.__parse_operator_structure(t, i)
                except RuntimeError as _:
                    return None
            elif t.type == TokenType.ExpressionSeparator:
                break

            else:
                val = self.__parse_value(t)
                self.stack.append(val)

            if self.workingOperator and len(self.workingOperator.operands) == self.workingOperator.operator.num_variables:
                op_head = self.workingOperator
                while op_head.parse_parent is not None:
                    op_head = op_head.parse_parent
                return op_head

            if len(self.stack) == 1 and self.workingOperator is None:
                return self.stack[0]

        if self.workingOperator and len(self.stack) != 0 or not self.workingOperator and len(self.stack) != 1:
            return None
        if self.workingOperator and len(self.workingOperator.operands) < self.workingOperator.operator.num_variables:
            return None

        if self.workingOperator:
            return self.workingOperator

        return self.stack[0]

    def parse(self) -> ValueToken | OperatorInstance:
        self.workingOperator: ValueToken | OperatorInstance | None = None

        result = self.parse_until_full_tree()
        while not self.tokens.done() and self.tokens.peek().type != TokenType.ExpressionSeparator and result is not None:
            r = self.parse_until_full_tree()
            if r is None:
                break
            result = r


        if result is None:
            raise RuntimeError(f'Could not parse expression')

        return result


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

        self.expression_parser.set_tokens_and_context(self.tokens, self.context)
        expr = self.expression_parser.parse()

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
