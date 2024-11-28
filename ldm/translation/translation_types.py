from __future__ import annotations
from enum import Enum
from dataclasses import dataclass


class TranslationStructureComponentType(Enum):
    String = 1
    Variable = 2
    Whitespace = 3


@dataclass
class TranslationStructureComponent:
    component_type: TranslationStructureComponentType
    value: str
    inner_structure: list[TranslationStructureComponent] | None = None
    inner_fields: dict[str, str] | None = None


def parse_translate_into_components(structure: str) -> list[TranslationStructureComponent]:
    components: list[TranslationStructureComponent] = []

    running_word = ''
    is_var = False

    def add_component():
        nonlocal running_word, is_var
        if running_word != '':
            if is_var:
                components.append(TranslationStructureComponent(TranslationStructureComponentType.Variable, running_word[1:]))
            else:
                components.append(TranslationStructureComponent(TranslationStructureComponentType.String, running_word))
        running_word = ''
        is_var = False

    for char in (structure + ' '):
        if char in ' \t\n\r':
            add_component()
            components.append(TranslationStructureComponent(TranslationStructureComponentType.Whitespace, char))

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
class PrimitiveTypeTranslation:
    type: str
    name: str
    translate: str


@dataclass
class ValueKeywordTranslation:
    type: str
    name: str
    translate: str


@dataclass
class OperatorTranslation:
    type: str
    name: str
    translate: list[TranslationStructureComponent]


@dataclass
class StructuredObjectTranslation:
    type: str
    name: str
    translate: list[TranslationStructureComponent]


@dataclass
class BlockTranslation:
    type: str
    name: str
    translate: list[TranslationStructureComponent]
    inner_indent: int
