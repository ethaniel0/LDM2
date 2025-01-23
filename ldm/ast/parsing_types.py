from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from ldm.lib_config2.spec_parsing import string_to_typespec
from ldm.source_tokenizer.tokenizer_types import Token
from ldm.lib_config2.parsing_types import Spec, TypeSpec, StructuredObject, ComponentType, \
    StructureComponentType, StructureComponent, OperatorType


class TokenIterator:
    def __init__(self, tokens: list[Token]):
        self.tokens = [*tokens]
        self.index = 0

    def __next__(self) -> tuple[Token, int]:
        if self.index >= len(self.tokens):
            raise StopIteration

        return_value = self.tokens[self.index], self.index

        self.index += 1
        return return_value

    def __iter__(self):
        return self

    def done(self):
        return self.index >= len(self.tokens)

    def goto(self, index: int):
        self.index = index

    def current_index(self):
        return self.index

    def peek(self, index: int = -1) -> Token | None:
        if index == -1:
            index = self.index

        if index >= len(self.tokens):
            return None

        return self.tokens[index]

@dataclass
class ParsingItems:
    config_spec: Spec


@dataclass
class ParsingContext:
    variables: dict[str, TypeSpec]
    """Dictionary of variables in the current scope"""
    parent: ParsingContext | None
    """The parent context, if this context is a sub-scope"""

    def __init__(self, parent=None):
        self.variables = {}
        self.parent = parent

    def has_local(self, key):
        """Check if a variable is defined in the current scope"""
        return key in self.variables

    def has_global(self, key):
        """Check if a variable is defined in the current scope or any parent scope"""
        if key in self.variables:
            return True
        if self.parent is not None:
            return self.parent.has_global(key)
        return False

    def get_local(self, key):
        """Get the type of some variable defined in the current scope"""
        if key in self.variables:
            return self.variables[key]
        return None

    def get_global(self, key):
        """Get the type of a variable defined in the current scope or any parent scope"""
        if key in self.variables:
            return self.variables[key]
        if self.parent is not None:
            return self.parent.get_global(key)
        return None

@dataclass
class ValueToken:
    value: Token  # This could be a literal or variable name, depending on your language
    var_type: TypeSpec
    parse_parent: StructuredObjectInstance | None

    def __str__(self):
        return f"ValueToken({self.value.value}: {self.var_type})"

    def __repr__(self):
        return f"{{{self.value.value}}}"


@dataclass
class SOInstanceItem:
    """Structured Object Instance Item"""
    item_type: ComponentType
    """The type of the item (name, typename, expression, etc.)"""
    value: Any
    """The value of the item"""
    token: Token
    created_context: ParsingContext | None = None
    """If the item created a local context (ex. function body), the ending result of that context is stored here."""


class NameInstance(SOInstanceItem):
    """Structured Object Instance Item for a name (string name of variable)"""
    def __init__(self, item_type: ComponentType, value: str, token: Token):
        super().__init__(item_type, value, token)


class TypenameInstance(SOInstanceItem):
    """Structured Object Instance Item for a typename (TypeSpec)"""
    def __init__(self, item_type: ComponentType, value: TypeSpec, token: Token):
        super().__init__(item_type, value, token)

@dataclass
class OperatorFields:
    result_type: TypeSpec
    op_type: OperatorType
    parse_parent: SOInstanceItem | None = None

@dataclass
class StructuredObjectInstance:
    """An instance of a structured object"""
    so: StructuredObject
    """The structured object that this instance represents"""
    components: dict[str, SOInstanceItem]
    """Dictionary of components, as [component name: component instance object]"""
    variable_attributes: dict[str, TypeSpec] | None = None
    """Attributes attached to a variable, if any."""
    operator_fields: OperatorFields | None = None
    """Fields needed for an operator, if any."""

    def __init__(self, so: StructuredObject, components: dict[str, SOInstanceItem]):
        self.so = so
        self.components = components
        if not so.create_operator:
            return

        first_is_expression = so.structure.component_defs[0].component_type == StructureComponentType.Variable and \
                              so.get_nth_component(0).base == ComponentType.EXPRESSION
        last_is_expression = so.structure.component_defs[-1].component_type == StructureComponentType.Variable and \
                             so.get_nth_component(-1).base == ComponentType.EXPRESSION

        if first_is_expression and last_is_expression:
            op_type = OperatorType.BINARY
        elif first_is_expression and not last_is_expression:
            op_type = OperatorType.UNARY_LEFT
        elif not first_is_expression and last_is_expression:
            op_type = OperatorType.UNARY_RIGHT
        else:
            op_type = OperatorType.INTERNAL

        self.operator_fields = OperatorFields(TypeSpec("", 0, []), op_type)

    def clone(self):
        return StructuredObjectInstance(self.so, {})

    def get_nth_component(self, n: int):
        defs = self.so.structure.component_defs
        def_vars: list[StructureComponent] = list(
            filter(lambda v: v.component_type == StructureComponentType.Variable, defs)
        )
        sc = def_vars[n]
        return self.components[sc.value]

    def operator_fields_filled(self):
        if not self.so.create_operator:
            raise RuntimeError(f'{self.so.name} is not an operator')
        fields = self.so.create_operator.fields
        total = 0
        for field in fields:
            components = self.extract_from_path(field)
            if components is not None:
               total += 1
        return total

    def operator_num_lefts(self):
        num = 0
        for d in self.so.structure.component_defs:
            if d.component_type == StructureComponentType.Variable and \
                    self.so.structure.component_specs[d.value].base == ComponentType.EXPRESSION:
                num += 1
            else:
                break
        return num

    def extract_from_path(self, path: str) -> ValueError | list[SOInstanceItem] | list[str]:
        if path.startswith('$'):
            path = path[1:]

        parts = path.split('.')
        item = self.components[parts[0]]

        stack = [item]

        for p_num in range(1, len(parts)):
            p = parts[p_num]
            sub_items = []
            for stack_item in stack:
                if stack_item.item_type == ComponentType.REPEATED_ELEMENT:
                    for i in range(len(stack_item.value)):
                        if p not in stack_item.value[i].components:
                            return ValueError(f'item {p_num+1} ({p}) not found in {path}')
                        sub_item = stack_item.value[i].components[p]
                        sub_items.append(sub_item)
                else:
                    if p not in stack_item.value:
                        return ValueError(f'item {p_num+1} ({p}) not found in {path}')
                    sub_item = stack_item.value[p]
                    sub_items.append(sub_item)
            stack = sub_items

        variables = []

        for item in stack:
            variables.append(item)

        return variables

    def __str__(self):
        return f"StructuredObjectInstance({self.so.name} {self.components})"

    def __repr__(self):
        return f"StructuredObjectInstance({self.so.name})"

