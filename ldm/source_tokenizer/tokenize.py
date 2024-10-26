from .tokenizer_types import Token, TokenType
from ldm.lib_config2.parsing_types import PrimitiveType
from dataclasses import dataclass


@dataclass
class TokenizerItems:
    primitive_types: list[PrimitiveType]


def tokenize(source: str, items: TokenizerItems) -> list[Token]:
    tokens = []

    in_str = False
    in_number = False
    in_float = False
    in_identifier = False
    in_operator = False
    running_str = ""

    def reset_state():
        nonlocal in_str, in_number, in_float, in_identifier, in_operator, running_str
        in_str = False
        in_number = False
        in_float = False
        in_identifier = False
        in_operator = False
        running_str = ""

    index = 0
    line = 0

    numbers = "1234567890"
    alphabet = "_qwertyuiopasdfghjklzxcvbnmQWERTYUIOOPLKJHGFDSAZXCVBNM"
    whitespace = " \t\n"

    char_ind = 0

    while char_ind < len(source):
        c = source[char_ind]
        char_ind += 1
        if c == "\n":
            line += 1
            index = 0
        index += 1
        if len(running_str) == 0:
            if c in whitespace:
                continue
            if c == "\"":
                in_str = True
                continue
            if c in numbers:
                in_number = True
                running_str += c
                continue
            if c in alphabet:
                in_identifier = True
                running_str += c
                continue
            if c in '{}()':
                match c:
                    case '{':
                        tokens.append(Token(TokenType.LBRACKET, c, line))
                    case '}':
                        tokens.append(Token(TokenType.RBRACKET, c, line))
                    case '(':
                        tokens.append(Token(TokenType.LPAREN, c, line))
                    case ')':
                        tokens.append(Token(TokenType.RPAREN, c, line))
                continue

            running_str += c
            in_operator = True
            continue

        if in_str:
            if c == "\"":
                tokens.append(Token(TokenType.String, running_str, line))
                reset_state()
            elif c == '\n':
                raise ValueError(f"Unexpected newline in string at line {line-1}")
            else:
                running_str += c
            continue

        elif in_number:
            if c in numbers:
                running_str += c
            elif c == '.':
                if in_float:
                    raise ValueError(f"Unexpected . in number at line {line-1}")
                in_float = True
                running_str += c
            elif c in alphabet:
                raise ValueError(f"Unexpected character in number at line {line-1}")
            else:
                num_type = TokenType.Float if in_float else TokenType.Integer
                tokens.append(Token(num_type, running_str, line))
                reset_state()
                char_ind -= 1
            continue

        elif in_identifier:
            if c in alphabet or c in numbers:
                running_str += c
            else:
                is_primitive_type = any([pt.name == running_str for pt in items.primitive_types])
                is_identifier = False
                if not is_primitive_type:
                    is_identifier = True

                token_type = TokenType.Identifier
                if is_primitive_type:
                    token_type = TokenType.PrimitiveType
                elif is_identifier:
                    token_type = TokenType.Identifier

                tokens.append(Token(token_type, running_str, line))
                reset_state()
                char_ind -= 1
            continue

        elif in_operator:
            if c not in alphabet and c not in numbers and c not in whitespace:
                running_str += c
            else:
                tokens.append(Token(TokenType.Operator, running_str, line))
                reset_state()
                char_ind -= 1
            continue

    if in_str:
        raise ValueError(f"Unterminated string at line {line-1}")
    if in_number:
        num_type = TokenType.Float if in_float else TokenType.Integer
        tokens.append(Token(num_type, running_str, line))
    if in_identifier:
        is_primitive_type = any([pt.name == running_str for pt in items.primitive_types])
        is_identifier = False
        if not is_primitive_type:
            is_identifier = True

        token_type = TokenType.Identifier
        if is_primitive_type:
            token_type = TokenType.Type
        elif is_identifier:
            token_type = TokenType.Identifier

        tokens.append(Token(token_type, running_str, line))
    if in_operator:
        tokens.append(Token(TokenType.Operator, running_str, line))

    return tokens
