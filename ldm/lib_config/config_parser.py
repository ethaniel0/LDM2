from __future__ import annotations
from dataclasses import dataclass
from .config_token import Command, ConfigItem
from .config_type import Type
from .config_error import ParsingError


class PromotionRule:
    def __init__(self, from_type, to_type):
        self.from_type = from_type
        self.to_type = to_type

    def validate(self):
        # Validate the promotion rule
        pass


class PromotionRuleGroup:
    def __init__(self, name: str, rules: list[PromotionRule]):
        self.rules = rules
        self.name = name

    @staticmethod
    def process(item: ConfigItem) -> PromotionRuleGroup | ParsingError:
        if item.class_type.token != 'promotion_rule':
            return ParsingError(f'Item of class {item.class_type} is not a promotion rule group on line {item.class_type.line}')

        if len(item.specifiers) != 1:
            return ParsingError(f'Promotion rule group on line {item.class_type.line} must have a name')

        name = item.specifiers[0].token
        rules = []

        for command in item.commands:
            if command.name != 'from':
                return ParsingError(f'Promotion rule group on line {item.class_type.line} must have only rule commands')

            if len(command.args) > 0:
                return ParsingError(f'Promotion rule on line {command.line} does not take arguments')

            if len(command.inner) != 2:
                return ParsingError(f'Promotion rule on line {command.line} must have exactly two arguments')

            from_type = command.args[0].token
            to_type = command.args[1].token

            rules.append(PromotionRule(from_type, to_type))



@dataclass
class Keyword:
    name: str
    structure: Command

    @staticmethod
    def process(item: ConfigItem) -> Keyword | ParsingError:
        if item.class_type.token != 'keyword':
            return ParsingError(f'Item of class {item.class_type} is not a keyword on line {item.class_type.line}')

        if len(item.specifiers) != 1:
            return ParsingError(f'Keyword definition on line {item.class_type.line} must have structure: keyword <name> (...)')

        name = item.specifiers[0].token

        if len(item.commands) != 1:
            return ParsingError(f'Keyword definition on line {item.class_type.line} must have exactly one structure')

        structure = item.commands[0]
        if structure.name != 'structure':
            return ParsingError(f'Keyword definition on line {item.class_type.line} must have structure: structure (...)')

        return Keyword(name, structure)


@dataclass
class Operator:
    symbol: str
    precedence: int
    structures: list[Command]
    return_type: str

    @staticmethod
    def process(item: ConfigItem) -> Operator | ParsingError:
        if item.class_type.token != 'operator':
            return ParsingError(f'Item of class {item.class_type} is not an operator on line {item.class_type.line}')

        if len(item.specifiers) != 1:
            return ParsingError(f'Operator definition on line {item.class_type.line} must have structure: operator <symbol> (...)')

        symbol = item.specifiers[0].token

        precedence: None | int = None
        structures: list[Command] = []
        returns = None

        if returns is None:
            return ParsingError(f'Operator definition on line {item.class_type.line} must have a return type')

        if precedence is None:
            return ParsingError(f'Operator definition on line {item.class_type.line} must have a precedence')

        if len(structures) == 0:
            return ParsingError(f'Operator definition on line {item.class_type.line} must have at least one structure')


        return Operator(symbol, precedence, structures, returns)


def parse_config(config: list[ConfigItem]) -> list[Type]:
    types = []

    for item in config:
        if item.class_type == 'type':
            t = Type.process(item)
            if type:
                types.append(t)

    return types
