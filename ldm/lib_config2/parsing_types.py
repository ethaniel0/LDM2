from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

# SPECS

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


@dataclass
class ValueKeyword:
    name: str
    value_type: str


@dataclass
class PrimitiveTypeInitialize:
    type: str


@dataclass
class PrimitiveType:
    name: str
    methods: list[Method]
    initialize: PrimitiveTypeInitialize
    value_keywords: list[ValueKeyword]
    superclass: str


@dataclass
class StructureSpecComponent:
    base: str
    name: str
    other: dict[str, str]


@dataclass
class MakeVariable:
    name: str
    structure: Structure


@dataclass
class Spec:
    primitive_types: dict[str, PrimitiveType]
    make_variables: dict[str, MakeVariable]
    initializer_formats: dict[str, InitializationSpec]


# DEFINITIONS
class StructureComponentType(Enum):
    String = 1
    Variable = 2
    Command = 3
    EndCommand = 4


@dataclass
class StructureComponent:
    component_type: StructureComponentType
    value: str


@dataclass
class Structure:
    component_specs: dict[str, StructureSpecComponent]
    component_defs: list[StructureComponent]


class InitializationType(Enum):
    VARIABLE = 0
    LITERAL = 1


@dataclass
class InitializationSpec:
    ref_type: str
    init_type: InitializationType
    format: str


@dataclass
class TypeTreeNode:
    type: PrimitiveType
    parent: TypeTreeNode | None
    children: list[TypeTreeNode]

