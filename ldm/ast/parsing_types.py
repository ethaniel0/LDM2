from __future__ import annotations
from dataclasses import dataclass
from ldm.source_tokenizer.tokenizer_types import Token
from ldm.lib_config2.parsing_types import Spec


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


@dataclass
class ParsingItems:
    config_spec: Spec


@dataclass
class ParsingContext:
    variables: dict[str, str]
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


class ExpressionToken(Token):
    def __init__(self, token: Token, var_type: str):
        super().__init__(token.type, token.value, token.line)
        self.var_type = var_type


@dataclass
class MakeVariableInstance:
    structure: dict[str, Token]
    name: str
    typename: Token
    varname: Token
    expr: Token

    def __init__(self, name: str, structure: dict[str, Token]):
        self.structure = structure
        if 'typename' not in structure:
            raise RuntimeError(f'typename variable not found in Make Variable structure "{name}"')
        elif 'varname' not in structure:
            raise RuntimeError(f'varname variable not found in Make Variable structure "{name}"')
        elif 'expr' not in structure:
            raise RuntimeError(f'expr variable not found in Make Variable structure "{name}"')

        self.typename = structure['typename']
        self.varname = structure['varname']
        self.expr = structure['expr']
        self.name = name
