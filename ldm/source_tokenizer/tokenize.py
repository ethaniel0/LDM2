from .tokenizer_types import Token, TokenType
from ldm.lib_config2.parsing_types import PrimitiveType, Operator, ExpressionSeparator, Keyword
from dataclasses import dataclass


@dataclass
class TokenizerItems:
    primitive_types: dict[str, PrimitiveType]
    operators: dict[str, Operator]
    keywords: dict[str, Keyword]
    expression_separators: dict[str, ExpressionSeparator]


class Tokenizer:
    def __init__(self, items: TokenizerItems):
        self.items = items
        self.source = ""
        self.tokens = []

        self.in_str = False
        self.in_number = False
        self.in_float = False
        self.in_identifier = False
        self.in_operator = False
        self.running_str = ""

        self.index = 0
        self.line = 1

        self.NUMBERS = "1234567890"
        self.ALPHABET = "_qwertyuiopasdfghjklzxcvbnmQWERTYUIOOPLKJHGFDSAZXCVBNM"
        self.WHITESPACE = " \t\n\r"

        self.char_ind = 0

    def __add_bracket(self, c: str):
        match c:
            case '{':
                self.tokens.append(Token(TokenType.LBRACKET, c, self.line))
            case '}':
                self.tokens.append(Token(TokenType.RBRACKET, c, self.line))

    def __handle_str(self, c: str):
        if c == "\"":
            self.tokens.append(Token(TokenType.String, self.running_str, self.line))
            self.__reset_state()
        elif c == '\n' or c == '\0':
            raise ValueError(f"Unexpected newline in string at line {self.line - 1}")
        else:
            self.running_str += c

    def __handle_number(self, c: str):
        if c in self.NUMBERS:
            self.running_str += c
        elif c == '.':
            if self.in_float:
                raise ValueError(f"Unexpected . in number at line {self.line - 1}")
            self.in_float = True
            self.running_str += c
        elif c in self.ALPHABET:
            raise ValueError(f"Unexpected character in number at line {self.line - 1}")
        else:
            num_type = TokenType.Float if self.in_float else TokenType.Integer
            self.tokens.append(Token(num_type, self.running_str, self.line))
            self.__reset_state()
            self.char_ind -= 1
            self.eat(c)

    def __get_identifier_type(self):
        # check is primitive type
        if self.running_str in self.items.primitive_types:
            return TokenType.PrimitiveType

        # check is operator
        is_operator = any(o.trigger == self.running_str for o in self.items.operators.values())
        if is_operator:
            return TokenType.Operator

        is_keyword = any(k.trigger == self.running_str for k in self.items.keywords.values())
        if is_keyword:
            return TokenType.Keyword

        # check is value keyword
        for pt in self.items.primitive_types.values():
            for vk in pt.value_keywords:
                if vk.name == self.running_str:
                    return TokenType.ValueKeyword

        return TokenType.Identifier

    def __handle_identifier(self, c: str):
        if c in self.ALPHABET or c in self.NUMBERS:
            self.running_str += c
            return

        token_type = self.__get_identifier_type()

        self.tokens.append(Token(token_type, self.running_str, self.line))
        self.__reset_state()
        self.char_ind -= 1
        self.eat(c)

    def __handle_operator(self, c: str):
        if c != '\0' and c not in self.ALPHABET and c not in self.NUMBERS and c not in self.WHITESPACE:
            self.running_str += c
        else:
            self.tokens.append(Token(TokenType.Operator, self.running_str, self.line))
            self.__reset_state()
            self.char_ind -= 1
            self.eat(c)

    def eat(self, c: str):
        self.char_ind += 1
        if c == "\n":
            self.line += 1
            self.index = 0
        self.index += 1

        if len(self.running_str) == 0:
            if c in self.items.expression_separators:
                self.tokens.append(Token(TokenType.ExpressionSeparator, c, self.line))
                return
            
            if c in self.WHITESPACE:
                return
            if c == "\"":
                self.in_str = True
                return
            if c in self.NUMBERS:
                self.in_number = True
                self.running_str += c
                return
            if c in self.ALPHABET:
                self.in_identifier = True
                self.running_str += c
                return
            if c in '{}':
                self.__add_bracket(c)
                return

            self.running_str += c
            self.in_operator = True
            return

        if self.in_str:
            self.__handle_str(c)

        elif self.in_number:
            self.__handle_number(c)

        elif self.in_identifier:
            self.__handle_identifier(c)

        elif self.in_operator:
            self.__handle_operator(c)

        else:
            raise ValueError("Invalid state?")

    def tokenize(self, source: str):
        self.__reset_state()
        self.tokens = []
        self.line = 1
        self.index = 0
        self.char_ind = 0
        self.source = source

        for c in source:
            self.eat(c)

        return self.finish()

    def finish(self):
        if self.in_str:
            raise ValueError(f"Unterminated string at line {self.line - 1}")
        self.eat('\0')
        return self.tokens

    def __reset_state(self):
        self.in_str = False
        self.in_number = False
        self.in_float = False
        self.in_identifier = False
        self.in_operator = False
        self.running_str = ""
