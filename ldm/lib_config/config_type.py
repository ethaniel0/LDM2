from __future__ import annotations
from dataclasses import dataclass
from .config_token import Command, BracketItem, ConfigItem, CommandItemType
from .config_error import ParsingError

@dataclass
class MethodArgument:
    name: str
    type: str
    optional: bool


@dataclass
class Method:
    name: str
    args: list[MethodArgument]
    return_type: str

    @staticmethod
    def process(cmd: Command) -> Method | ParsingError:
        # Process the config item into a Method
        if cmd.name != 'method':
            return ParsingError('Command is not a method')

        args = []

        # get command args = [return_type, name]
        if len(cmd.args) != 2:
            return ParsingError(f'Method command must have format of {{return_type name}} on line {cmd.line}')
        return_type = cmd.args[0].token
        name = cmd.args[1].token

        for item in cmd.inner:
            if item.item_type != CommandItemType.Bracketed:
                return ParsingError('Method block only takes arg blocks')
            bracket: BracketItem = item.item
            if len(bracket.inner) < 3 or len(bracket.inner) > 4:
                return ParsingError(f'Method block has format of {{arg optional? type name}} on line {cmd.line}')

            bracket_type = bracket.inner[0]
            if bracket_type.token != 'arg':
                return ParsingError('Method block only takes arg blocks')

            if len(bracket.inner) == 3:
                arg_type = bracket.inner[1].token
                arg_name = bracket.inner[2].token
                arg_optional = False

            else:
                if bracket.inner[1].token != 'optional':
                    return ParsingError(f'token {bracket.inner[1].token} not recognized on line {cmd.line}, '
                                        f'did you mean to type \'optional\'?')
                arg_type = bracket.inner[2].token
                arg_name = bracket.inner[3].token
                arg_optional = True

            args.append(MethodArgument(arg_name, arg_type, arg_optional))

        return Method(name, args, return_type)


@dataclass
class Type:
    name: str
    methods: list[Method]
    initialize: Command

    @staticmethod
    def process(item: ConfigItem) -> Type | ParsingError:
        # Process the config item into a Type
        if item.class_type.token != 'type':
            return ParsingError(f'Item of class {item.class_type} is not a type on line {item.class_type.line}')

        if len(item.specifiers) != 1:
            return ParsingError(f'Type definition on line {item.class_type.line} must have structure: type <name> (...)')

        name = item.specifiers[0].token

        initialize: Command | None = None
        methods: list[Method] = []

        for command in item.commands:
            if command.name == 'initialize':
                initialize = command
            elif command.name == 'method':
                method = Method.process(command)
                if isinstance(method, ParsingError):
                    return method
                if method:
                    methods.append(method)

        return Type(name, methods, initialize)

