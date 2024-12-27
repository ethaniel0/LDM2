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
    ExpressionSeparator = "separator",

    LBRACKET = "[",
    RBRACKET = "]",

    LPAREN = "(",
    RPAREN = ")",


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    char: int

    def __repr__(self):
        return f"Token<{self.type}, {self.value}>"

    def __eq__(self, other):
        return self.type == other.type and self.value == other.value
