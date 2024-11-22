from __future__ import annotations
from ldm.source_tokenizer.tokenize import Token, TokenType
from ldm.ast.parsing_types import (TokenIterator, ParsingItems, ParsingContext,
                                   OperatorInstance, ValueToken)
from ldm.lib_config2.parsing_types import StructureComponentType, TypeSpec, OperatorType


class ExpressionParser:
    def __init__(self, items: ParsingItems):
        self.items = items
        self.stack: list[ValueToken | OperatorInstance] = []
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
                    possible_operators.append(OperatorInstance(op, [], '', None, token))
                elif has_left and (
                    op.operator_type == OperatorType.UNARY_LEFT or
                    op.operator_type == OperatorType.BINARY
                ):
                    possible_operators.append(OperatorInstance(op, [], '', None, token))

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

            components_parsed = 0
            components_needed = len(op_components) - index

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
                        components_parsed += 1
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
                            components_parsed += 1
                        else:
                            break
                    else:
                        new_tree = ep.parse_until_full_tree()
                        while new_tree is not None:
                            tree = new_tree
                            new_tree = ep.parse_until_full_tree()
                        op.operands.append(tree)
                        components_parsed += 1

                else:
                    if not self.tokens.peek() or comp.value != self.tokens.peek().value:
                        break
                    components_parsed += 1
                    next(self.tokens)

            if components_parsed != components_needed:
                break

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

        raise RuntimeError(f'Could not parse value "{token.value}" at line {token.line}')

    def set_tokens_and_context(self, tokens: TokenIterator, context: ParsingContext):
        self.tokens = tokens
        self.parsing_context = context

    def __get_op_head(self):
        op_head = self.workingOperator
        while op_head.parse_parent is not None:
            op_head = op_head.parse_parent
        return op_head

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
                return self.__get_op_head()

            if len(self.stack) == 1 and self.workingOperator is None:
                return self.stack[0]

        if self.workingOperator and len(self.stack) != 0 or not self.workingOperator and len(self.stack) != 1:
            return None
        if self.workingOperator and len(self.workingOperator.operands) < self.workingOperator.operator.num_variables:
            return None

        if self.workingOperator:
            return self.workingOperator

        return self.stack[0]

    def parse(self, until="", singular=True) -> ValueToken | OperatorInstance | list[ValueToken | OperatorInstance]:
        self.workingOperator: ValueToken | OperatorInstance | None = None
        self.stack = []

        result = None
        while not self.tokens.done() and self.tokens.peek().type != TokenType.ExpressionSeparator:
            if until and self.tokens.peek().value == until:
                break
            r = self.parse_until_full_tree()
            if r is None and result is None:
                raise RuntimeError(f'Could not parse expression starting with token {self.tokens.peek()} at line {self.tokens.peek().line}')
            if r is None and isinstance(result, OperatorInstance):
                self.stack.append(result)
            result = r

        if not self.tokens.done() and self.tokens.peek().type == TokenType.ExpressionSeparator:
            next(self.tokens)

        if singular and len(self.stack) > 1:
            if isinstance(self.stack[0], ValueToken):
                raise RuntimeError(f'Expression does not simplify to a singular value at {self.stack[0].value.line}')
            raise RuntimeError(f'Expression does not simplify to a singular value at {self.stack[0].token.line}')

        if len(self.stack) == 0 and self.workingOperator:
            return self.__get_op_head()

        if singular:
            return self.stack[0]
        return self.stack
