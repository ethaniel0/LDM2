from __future__ import annotations
from ldm.source_tokenizer.tokenize import Token, TokenType
from ldm.ast.parsing_types import (TokenIterator, ParsingItems, ParsingContext,
                                   OperatorInstance, ValueToken, StructuredObjectInstance,
                                   SOInstanceItem)
from ldm.lib_config2.parsing_types import StructureComponentType, TypeSpec, OperatorType, Associativity, ComponentType
from ldm.ast.type_checking import type_operator

class ExpressionParser:
    def __init__(self, items: ParsingItems):
        self.items = items
        self.stack: list[ValueToken | StructuredObjectInstance] = []
        self.workingOperator: ValueToken | StructuredObjectInstance | None = None
        self.tokens = TokenIterator([])
        self.parsing_context = ParsingContext()

    def __create_operator_list(self, token: Token) -> list[StructuredObjectInstance]:
        if token.type != TokenType.Operator:
            return []

        possible_operators: list[StructuredObjectInstance] = []

        has_left = False
        """if the operator must take a variable to its left"""

        if self.workingOperator is not None and \
                self.workingOperator.operator_fields_filled() == len(self.workingOperator.so.create_operator.fields):
            has_left = True

        elif not self.workingOperator and len(self.stack) > 0:
            has_left = True

        for op in self.items.config_spec.structured_objects.values():
            if not op.create_operator:
                continue

            soi = StructuredObjectInstance(op, {})

            if (has_left and soi.operator_fields.op_type in [OperatorType.UNARY_LEFT, OperatorType.BINARY]) or \
                (not has_left and soi.operator_fields.op_type in [OperatorType.UNARY_RIGHT, OperatorType.INTERNAL]):

                possible_operators.append(soi)

        return possible_operators

    def __parse_operator_structure(self, op_token: Token, op_index: int):
        ops = self.__create_operator_list(op_token)

        if len(ops) == 0:
            raise RuntimeError(f'Operator {op_token} not defined at line {op_token.line}')

        working_ops = []
        ending_indices = []

        # try parsing for each operator, if parsing works for the operator's whole structure, add it to working_ops
        for op in ops:
            op_has_left = op.operator_fields.op_type in [OperatorType.UNARY_LEFT, OperatorType.BINARY]
            op_components = op.so.structure.component_defs
            index = 0
            # operators are recognized by their non-variable components,
            # so the previous variable components (which have already been parsed) are skipped
            for i in op_components:
                index += 1
                if i.component_type != StructureComponentType.Variable:
                    break

            components_parsed = 0
            components_needed = len(op_components) - index

            # parse (recursively) the operator's structure
            for i in range(index, len(op_components)):
                comp = op_components[i]
                # if next structure component is a variable, parse new expression
                if comp.component_type == StructureComponentType.Variable:
                    ep = ExpressionParser(self.items)
                    ep.set_tokens_and_context(self.tokens, self.parsing_context)

                    first_token = self.tokens.peek()

                    # parse_until_full_tree only parses until the next value or operator or expression separator,
                    # so it doesn't parse any more than it needs to before checking for the next structure component
                    tree = ep.parse_until_full_tree()
                    if tree is None:
                        break

                    # if that's the end of the operator's structure,
                    # add the tree to the operator's operands and continue
                    if i == len(op_components) - 1:
                        op.components[comp.value] = SOInstanceItem(ComponentType.STRUCTURE, tree, first_token)
                        components_parsed += 1
                        continue

                    next_comp = op_components[i + 1]

                    # if the next component is a string,
                    # keep parsing until that string is found
                    # (or the expression ended / there's no more code left to parse)
                    if next_comp.component_type == StructureComponentType.String:
                        successful = True

                        while self.tokens.peek() and next_comp.value != self.tokens.peek().value:
                            new_tree = ep.parse_until_full_tree()
                            if new_tree is None:
                                successful = False
                                break
                            tree = new_tree

                        if successful:
                            op.components[comp.value] = SOInstanceItem(ComponentType.STRUCTURE, tree, first_token)
                            components_parsed += 1
                        else:
                            break
                    # if the next component is a variable (another expression), we need to be sure that the next part
                    # parsed shouldn't be part of the first expression -> keep adding to the current expression
                    # parse tree until the next value cannot be added to the current expression, and thus must be the
                    # start of the next expression
                    else:
                        new_tree = ep.parse_until_full_tree()
                        while new_tree is not None:
                            tree = new_tree
                            new_tree = ep.parse_until_full_tree()
                        op.components[comp.value] = SOInstanceItem(ComponentType.STRUCTURE, tree, first_token)
                        components_parsed += 1

                # if the next structure component is a string, check if the next token is that string
                else:
                    if not self.tokens.peek() or comp.value != self.tokens.peek().value:
                        break
                    components_parsed += 1
                    next(self.tokens)

            # continue to the next operator if the current operator's structure couldn't be fully parsed
            if components_parsed != components_needed:
                continue

            # if operator has all right components (first left has already been accounted for)
            if op_has_left and op.operator_fields_filled() == len(op.so.create_operator.fields) - 1:
                working_ops.append(op)
                ending_indices.append(self.tokens.current_index())
            # if operator has no left components and all components have been parsed
            elif not op_has_left and op.operator_fields_filled() == len(op.so.create_operator.fields):
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
                if len(working_ops[i].so.create_operator.fields) > max_components:
                    max_components = len(working_ops[i].so.create_operator.fields)
                    op_choice = working_ops[i]
                    self.tokens.goto(ending_indices[i])

        left_component = op_choice.so.structure.component_defs[0]
        has_left = left_component.component_type == StructureComponentType.Variable

        if self.workingOperator is None:
            if has_left:
                if len(self.stack) == 0:
                    raise RuntimeError(f'No left operand for operator {op_token} at line {op_token.line}')
                op_choice.operands.insert(0, self.stack.pop())
            self.workingOperator = op_choice
        else:
            if has_left:
                while op_choice.operator.precedence > self.workingOperator.operator.precedence or \
                        (op_choice.operator.precedence == self.workingOperator.operator.precedence and
                         op_choice.operator.associativity == Associativity.LEFT_TO_RIGHT) or \
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
                raise RuntimeError(f'{token} not defined at line {token.line}')
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

    def parse_until_full_tree(self) -> ValueToken | StructuredObjectInstance | None:
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

            if self.workingOperator and self.workingOperator.operator_fields_filled() == len(self.workingOperator.so.create_operator.fields):
                return self.__get_op_head()

            if len(self.stack) == 1 and self.workingOperator is None:
                return self.stack[0]

        if self.workingOperator and len(self.stack) != 0 or not self.workingOperator and len(self.stack) != 1:
            return None
        if self.workingOperator and self.workingOperator.operator_fields_filled() < len(self.workingOperator.so.create_operator.fields):
            return None

        if self.workingOperator:
            return self.workingOperator

        return self.stack[0]

    def parse(self, until="", singular=True) -> ValueToken | StructuredObjectInstance | list[ValueToken | OperatorInstance]:
        self.workingOperator: ValueToken | StructuredObjectInstance | None = None
        self.stack: list[ValueToken | StructuredObjectInstance] = []

        result: None | ValueToken | StructuredObjectInstance = None
        while not self.tokens.done() and self.tokens.peek().type != TokenType.ExpressionSeparator:
            if until and self.tokens.peek().value == until:
                break
            r = self.parse_until_full_tree()
            if r is None and result is None:
                raise RuntimeError(f'Could not parse expression starting with token {self.tokens.peek()} at line {self.tokens.peek().line}')
            if r is None and isinstance(result, StructuredObjectInstance):
                self.stack.append(result)
            result = r

        if not self.tokens.done() and self.tokens.peek().type == TokenType.ExpressionSeparator:
            next(self.tokens)

        if singular and len(self.stack) > 1:
            if isinstance(self.stack[0], ValueToken):
                raise RuntimeError(f'Expression does not simplify to a singular value at {self.stack[0].value.line}')
            first_stack_comp = self.stack[0]
            first_var = None
            for item in first_stack_comp.so.structure.component_defs:
                if item.component_type == StructureComponentType.Variable:
                    first_var = item
                    break
            first_comp = first_stack_comp.components[first_var.value]
            raise RuntimeError(f'Expression does not simplify to a singular value at {first_comp.token.line}')

        if len(self.stack) == 0 and self.workingOperator:
            op_head = self.__get_op_head()
            type_operator(op_head, self.items)
            return op_head

        if singular:
            return self.stack[0]
        return self.stack
