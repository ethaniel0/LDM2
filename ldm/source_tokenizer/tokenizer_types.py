import ldm.lib_config2.parsing_types as parsing_types
from enum import Enum
from dataclasses import dataclass


class TokenType(Enum):
    Identifier = "$name",
    Integer = "$int",
    Float = "$float",
    String = "$string",
    Operator = "$operator",
    Keyword = "$keyword",
    Type = "$typename",
    PrimitiveType = "typename",
    ValueKeyword = "value",

    LBRACKET = "[",
    RBRACKET = "]",

    LPAREN = "(",
    RPAREN = ")",


@dataclass
class Token:
    type: TokenType
    value: str
    line: int

    def __repr__(self):
        return f"Token<{self.type}, {self.value}>"

    def __eq__(self, other):
        return self.type == other.type and self.value == other.value
