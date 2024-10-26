import re
from dataclasses import dataclass
from enum import Enum
from json import load
from .parser.config_tokenizer import ConfigToken, ConfigTokenBuilder, ConfigTokenType
from .config_error import ParsingError

with open('BracketCommands.json') as f:
    _bracket_commands = load(f)

with open('commands.json') as f:
    _commands = load(f)


@dataclass
class BracketItem:
    inner: list[ConfigToken]

@dataclass
class Command:
    name: str
    line: int
    args: list[ConfigToken]
    inner: list['CommandItem']


class CommandItemType(Enum):
    Word = 1,
    Bracketed = 2,
    Command = 3


@dataclass
class CommandItem:
    item: ConfigToken | BracketItem | Command
    item_type: CommandItemType

    @staticmethod
    def new_word(word: ConfigToken):
        return CommandItem(word, CommandItemType.Word)

    @staticmethod
    def new_bracketed(word: BracketItem):
        return CommandItem(word, CommandItemType.Bracketed)

    @staticmethod
    def new_command(word: Command):
        return CommandItem(word, CommandItemType.Command)

    def __str__(self):
        return f"<{self.item}: {self.item_type.name}>"

    def __repr__(self):
        return str(self)


@dataclass
class ConfigItem:
    class_type: ConfigToken
    specifiers: list[ConfigToken]
    commands: list[Command]


class ConfigItemBuilder:
    def __init__(self, tokens: list[ConfigToken]):
        self.tokens = tokens
        self.index = 0

    def get_next_class_type(self) -> ConfigToken | None:
        if self.index >= len(self.tokens):
            return None
        if self.tokens[self.index].token_type != ConfigTokenType.StructureWord:
            return None
        t = self.tokens[self.index]
        self.index += 1
        return t

    def get_next_specifiers(self) -> list[ConfigToken] | None:
        specifiers: list[ConfigToken] = []

        while self.index < len(self.tokens) and self.tokens[self.index].token_type != ConfigTokenType.LParen:
            specifiers.append(self.tokens[self.index])
            self.index += 1

        if self.index >= len(self.tokens):
            return None

        self.index += 1
        return specifiers

    @staticmethod
    def search_open_close(tokens, open_value, close_value, start_index: int) -> int:
        open_count = 1
        index = start_index
        while open_count > 0 and index < len(tokens):
            if tokens[index] == open_value:
                open_count += 1
            elif tokens[index] == close_value:
                open_count -= 1
            index += 1
        return index - 1


    @staticmethod
    def parse_command(tokens: list[ConfigToken]) -> Command | ParsingError:
        if len(tokens) < 2:
            return ParsingError(f"Command must have at least a name and closing tag")
        if tokens[0].token_type != ConfigTokenType.Command:
            return ParsingError(f"Expected command name, got {tokens[0]}")
        if tokens[-1].token_type != ConfigTokenType.Percent:
            return ParsingError(f"Expected % at end of command, got {tokens[-1]}")

        name = tokens[0].token[1:]

        if name not in _commands:
            return ParsingError(f"Unexpected command {name} on line {tokens[0].line}")

        if re.match(_commands[name], "") is None:
            return ParsingError(f"Command {name} has incorrect inside structure {tokens[0].line}")



    @staticmethod
    def parse_commands(tokens: list[ConfigToken]) -> list[Command]:
        commands: list[Command] = []
        index = 0

        while index < len(tokens):
            token = tokens[index]
            if token.token_type != ConfigTokenType.Command:
                raise ValueError(f"Expected command, got {token}")
            name = token.token[1:]
            name_line = token.line
            index += 1

            if index >= len(tokens):
                raise ValueError(f"Expected command arguments, got end of file")

            if tokens[index].token_type == ConfigTokenType.Percent:
                if name not in _commands:
                    raise ValueError(f"Unexpected command {name} on line {token.line}")

                if re.match(_commands[name], "") is None:
                    raise ValueError(f"Command {name} must take arguments on line {token.line}")

                commands.append(Command(name, name_line, [], []))
                index += 1
                continue

            args = []
            # get arguments
            if tokens[index].token_type == ConfigTokenType.LParen:
                index += 1
                end_index = ConfigItemBuilder.search_open_close(
                    [t.token_type for t in tokens],
                    ConfigTokenType.LParen, ConfigTokenType.RParen,
                    index
                )
                if end_index >= len(tokens) or tokens[end_index].token_type != ConfigTokenType.RParen:
                    raise ValueError(f"Expected closing parenthesis, got end of file on line {token.line}")
                args = tokens[index:end_index]
                index = end_index + 1

            # if end of command, return command
            if index > len(tokens) or tokens[index].token_type == ConfigTokenType.Percent:
                commands.append(Command(name, name_line, args, []))
                index += 1
                continue

            # get inner part of command
            if index >= len(tokens):
                raise ValueError(f"Expected % at end of command on line {token.line}")

            if tokens[index].token_type == ConfigTokenType.Percent:
                commands.append(Command(name, name_line, args, []))
                index += 1
                continue

            if index >= len(tokens):
                raise ValueError(f"Expected a % at end of command on line {token.line}")

            inner: list[CommandItem] = []

            while index < len(tokens) and tokens[index].token_type != ConfigTokenType.Percent:
                t = tokens[index]
                if t.token_type == ConfigTokenType.Command:
                    end_index = ConfigItemBuilder.search_open_close(
                        [t.token_type for t in tokens],
                        ConfigTokenType.Command, ConfigTokenType.Percent,
                        index + 1
                    )
                    if end_index >= len(tokens) or tokens[end_index].token_type != ConfigTokenType.Percent:
                        raise ValueError(f"Expected a %, got end of file on line{t.line}")
                    inner_tokens = tokens[index:end_index+1]
                    index = end_index + 1

                    inner_commands = ConfigItemBuilder.parse_commands(inner_tokens)
                    inner.append(CommandItem.new_command(inner_commands[0]))

                elif t.token_type == ConfigTokenType.LBrace:
                    index += 1
                    end_index = ConfigItemBuilder.search_open_close(
                        [t.token_type for t in tokens],
                        ConfigTokenType.LBrace, ConfigTokenType.RBrace,
                        index
                    )
                    if end_index >= len(tokens) or tokens[end_index].token_type != ConfigTokenType.RBrace:
                        raise ValueError(f"Expected }}, got end of file on line {t.line}")

                    inner_tokens = tokens[index:end_index]
                    index = end_index + 1

                    inner_token_str = " ".join([t.token for t in inner_tokens]).strip()
                    bracket_name = inner_tokens[0].token
                    if bracket_name not in _bracket_commands:
                        raise ValueError(f"Unexpected bracket command {bracket_name} on line {t.line}")


                    inner_bracketed = BracketItem(inner_tokens)
                    inner.append(CommandItem.new_bracketed(inner_bracketed))

                elif t.token_type == ConfigTokenType.StructureWord:
                    inner.append(CommandItem.new_word(t))
                    index += 1

                else:
                    raise ValueError(f"Unexpected token {t}")

            if index >= len(tokens):
                raise ValueError(f"Expected % at end of command on line {token.line}")

            index += 1
            commands.append(Command(name, name_line, args, inner))

        return commands

    def next_config_item(self):
        if self.index >= len(self.tokens):
            return None

        class_type = self.get_next_class_type()
        specifiers = self.get_next_specifiers()
        next_index = self.search_open_close(
            [t.token_type for t in self.tokens],
            ConfigTokenType.LParen, ConfigTokenType.RParen,
            self.index
        )

        if next_index >= len(self.tokens) or self.tokens[next_index].token_type != ConfigTokenType.RParen:
            raise ValueError(f"Expected closing parenthesis, got end of file on line {class_type.line}")

        inner_tokens = self.tokens[self.index:next_index]

        self.index = next_index + 1

        commands = ConfigItemBuilder.parse_commands(inner_tokens)

        return ConfigItem(class_type, specifiers, commands)


def parse_config(source: str) -> list[ConfigItem]:
    tokens = ConfigTokenBuilder().get_tokens(source)
    items: list[ConfigItem] = []

    builder = ConfigItemBuilder(tokens)
    while item := builder.next_config_item():
        items.append(item)

    return items
