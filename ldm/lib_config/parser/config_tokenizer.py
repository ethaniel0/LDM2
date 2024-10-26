from dataclasses import dataclass
from enum import Enum



class ConfigTokenType(Enum):
    StructureWord = 1
    Command = 2
    Percent = 3
    LParen = 4
    RParen = 5
    LBrace = 6
    RBrace = 7


@dataclass
class ConfigToken:
    token: str
    token_type: ConfigTokenType
    line: int
    index: int

    def __str__(self):
        return f"<{self.token}: {self.token_type.name} at {self.line}:{self.index}>"

    def __repr__(self):
        return str(self)


class ConfigTokenBuilder:
    def __init__(self):
        self.running_str: str = ""
        self.index: int = 0
        self.line: int = 1
        self.in_cmd: bool = False
        self.in_num: bool = False
        self.in_non_alphnum: bool = False
        self.in_comment: bool = False
        self.tokens: list[ConfigToken] = []

    def __push_keyword(self):
        if self.running_str == '%':
            self.tokens.append(ConfigToken(self.running_str, ConfigTokenType.Percent, self.line, self.index))
        elif self.in_cmd:
            self.tokens.append(ConfigToken(self.running_str, ConfigTokenType.Command, self.line, self.index))
        elif len(self.running_str) > 0:
            self.tokens.append(ConfigToken(self.running_str, ConfigTokenType.StructureWord, self.line, self.index))
        self.running_str = ""
        self.in_cmd = False
        self.in_num = False
        self.in_non_alphnum = False

    def add_char(self, c: str):
        if len(c) != 1:
            raise ValueError("add_char must be called with a single character")
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        numbers = "0123456789"

        if c == '\n':
            self.line += 1
            self.index = 0
            if self.in_comment:
                self.in_comment = False
            self.__push_keyword()  # NOT IN RUST, seemed reasonable tho
        elif self.in_comment:
            return
        elif c == ' ' or c == '\t':
            self.__push_keyword()
        elif c == '%':
            if len(self.running_str) == 0:
                self.running_str += c
            else:
                self.__push_keyword()
                self.running_str += c
        elif c in '(){}':
            self.__push_keyword()
            options = {
                '(': ConfigTokenType.LParen,
                ')': ConfigTokenType.RParen,
                '{': ConfigTokenType.LBrace,
                '}': ConfigTokenType.RBrace
            }
            self.tokens.append(
                ConfigToken(c,
                            options[c],
                            self.line,
                            self.index
                            )
            )
        elif c in alphabet:
            if self.in_non_alphnum or self.in_num:
                self.__push_keyword()
            if self.running_str == '%':
                self.in_cmd = True
            self.running_str += c
        elif c in numbers:
            if self.in_non_alphnum:
                self.__push_keyword()
            if len(self.running_str) == 0:
                self.in_num = True
            self.running_str += c
        else:
            if c == '.' and self.in_num and '.' not in self.running_str:
                self.running_str += c
                return
            if len(self.running_str) == 0:
                self.in_non_alphnum = True
                self.running_str += c
                return
            if not self.in_non_alphnum:
                self.__push_keyword()

            self.running_str += c
            if self.running_str == '//':
                self.in_comment = True
                self.running_str = ""

    def finish(self):
        if len(self.running_str) > 0:
            self.__push_keyword()

    def reset(self):
        self.running_str = ""
        self.index = 0
        self.line = 1
        self.in_cmd = False
        self.in_num = False
        self.in_non_alphnum = False
        self.in_comment = False
        self.tokens = []

    def get_tokens(self, source: str):
        self.reset()
        for c in source:
            self.add_char(c)
            self.index += 1
        self.finish()
        return self.tokens
