from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from ldm.source_tokenizer.tokenizer_types import Token
from ldm.lib_config2.parsing_types import Spec, Operator, TypeSpec, StructuredObject, ComponentType


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
        """Get the type of a variable defined in the current scope"""
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
class OperatorInstance:
    operator: Operator
    '''The operator that this instance represents'''
    operands: list[ValueToken | OperatorInstance]
    '''List of parsed operands, each either a ValueToken or another OperatorInstance'''
    result_type: TypeSpec
    '''The type of the result of this operator'''
    parse_parent: OperatorInstance | None
    '''The parent operator instance, if this operator is a sub-expression'''
    token: Token | None
    '''The first string token that represents this operator'''

    def __str__(self):
        return f"OperatorInstance({self.operator.name})"

    def __repr__(self):
        return f"OperatorInstance({self.operator.name})"


@dataclass
class ValueToken:
    value: Token  # This could be a literal or variable name, depending on your language
    var_type: TypeSpec
    parse_parent: OperatorInstance | None

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


class NameInstance(SOInstanceItem):
    """Structured Object Instance Item for a name (string name of variable)"""
    def __init__(self, item_type: ComponentType, value: str):
        super().__init__(item_type, value)


class TypenameInstance(SOInstanceItem):
    """Structured Object Instance Item for a typename (TypeSpec)"""
    def __init__(self, item_type: ComponentType, value: TypeSpec):
        super().__init__(item_type, value)


@dataclass
class StructuredObjectInstance:
    """An instance of a structured object"""
    so: StructuredObject
    """The structured object that this instance represents"""
    components: dict[str, SOInstanceItem]
    """Dictionary of components, as [component name: component instance object]"""

    def __str__(self):
        return f"StructuredObjectInstance({self.so.name} {self.components})"

    def __repr__(self):
        return f"StructuredObjectInstance({self.so.name})"

