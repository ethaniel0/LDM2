from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from ldm.source_tokenizer.tokenizer_types import Token
from ldm.lib_config2.parsing_types import Spec, Operator, TypeSpec, Keyword, MakeVariable, BlockStructure


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
    parent: ParsingContext | None

    def __init__(self, parent=None):
        self.variables = {}
        self.parent = parent

    def has_local(self, key):
        return key in self.variables

    def has_global(self, key):
        if key in self.variables:
            return True
        if self.parent is not None:
            return self.parent.has_global(key)
        return False

    def get_local(self, key):
        if key in self.variables:
            return self.variables[key]
        return None

    def get_global(self, key):
        if key in self.variables:
            return self.variables[key]
        if self.parent is not None:
            return self.parent.get_global(key)
        return None


@dataclass
class OperatorInstance:
    operator: Operator
    operands: list[ValueToken | OperatorInstance]  # List of parsed operands, each either a ValueToken or another OperatorInstance
    result_type: TypeSpec
    parse_parent: OperatorInstance | None
    token: Token | None

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


class Structured:
    components: dict[str, Any]


@dataclass
class MakeVariableInstance:
    mv: MakeVariable
    components: dict[str, Token | ValueToken | OperatorInstance]

    def __str__(self):
        return f"MakeVariableInstance({self.mv.name} {self.components})"

    def __repr__(self):
        return f"MakeVariableInstance({self.mv.name})"


@dataclass
class KeywordInstance:
    keyword: Keyword
    components: dict[str, Token | ValueToken | OperatorInstance]
    token: Token | None

    def __str__(self):
        return f"KeywordInstance({self.keyword.name})"

    def __repr__(self):
        return f"KeywordInstance({self.keyword.name})"


@dataclass
class BlockInstance:
    block: BlockStructure
    components: dict[str, Token | ValueToken | OperatorInstance | list]
    token: Token | None

    def __str__(self):
        return f"BlockInstance({self.block.name})"

    def __repr__(self):
        return f"BlockInstance({self.block.name})"
