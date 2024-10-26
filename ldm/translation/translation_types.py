from enum import Enum
from dataclasses import dataclass


class StructureComponentType(Enum):
    String = 1
    Variable = 2
    Whitespace = 3


@dataclass
class StructureComponent:
    component_type: StructureComponentType
    value: str


def parse_translate_into_components(structure: str) -> list[StructureComponent]:
    components: list[StructureComponent] = []

    running_word = ''
    is_var = False

    def add_component():
        nonlocal running_word, is_var
        if running_word != '':
            if is_var:
                components.append(StructureComponent(StructureComponentType.Variable, running_word[1:]))
            else:
                components.append(StructureComponent(StructureComponentType.String, running_word))
        running_word = ''
        is_var = False

    for char in (structure + ' '):
        if char in ' \t\n\r':
            add_component()
            components.append(StructureComponent(StructureComponentType.Whitespace, char))

        elif running_word == '' and char == '$':
            running_word = char
            is_var = True
        elif running_word == '$' and char == '$':
            is_var = False
        elif is_var and not char.isalnum() and char != '_':
            add_component()
            running_word += char
        else:
            running_word += char

    return components[:-1]


@dataclass
class MakeVariableTranslation:
    type: str
    name: str
    translate: list[StructureComponent]


@dataclass
class PrimitiveTypeTranslation:
    type: str
    name: str
    translate: str


@dataclass
class ValueKeywordTranslation:
    type: str
    name: str
    translate: str
