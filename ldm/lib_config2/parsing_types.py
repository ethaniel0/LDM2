from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


# SPECS
@dataclass
class TypeSpec:
    name: str
    num_subtypes: int
    subtypes: list[TypeSpec]


@dataclass
class GeneralType(Protocol):
    spec: TypeSpec
    superclass: TypeSpec | None
    methods: list[Method]


@dataclass
class PrimitiveTypeInitialize:
    type: str


@dataclass
class PrimitiveType:
    spec: TypeSpec
    superclass: TypeSpec | None
    methods: list[Method]
    initialize: PrimitiveTypeInitialize
    value_keywords: list[ValueKeyword]


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
class StructureSpecComponent:
    base: str
    name: str
    other: dict[str, str]


@dataclass
class MakeVariable:
    name: str
    structure: Structure


@dataclass
class OperatorOverload:
    name: str
    return_type: str
    variables: dict[str, str]
    
    def __str__(self):
        return f"<{self.name}|{self.variables.values()}>"


class Associativity(Enum):
    LEFT_TO_RIGHT = 0
    RIGHT_TO_LEFT = 1
    NONE = 2


@dataclass
class Operator:
    name: str
    precedence: int
    structure: Structure
    overloads: list[OperatorOverload]
    trigger: str
    associativity: Associativity

    def overload_matches(self, overload: OperatorOverload):
        # Get all variable names from structure components
        structure_vars = set()
        for comp in self.structure.component_specs.values():
            if comp.base == "operator_value":
                structure_vars.add(comp.name)
        
        overload_vars = set(overload.variables.keys())
                
        # Check if all variables in overload exist in structure
        return structure_vars == overload_vars


@dataclass
class Spec:
    primitive_types: dict[str, PrimitiveType]
    '''{typename: PrimitiveType}'''
    make_variables: dict[str, MakeVariable]
    '''{MakeVariable name: MakeVariable}'''
    initializer_formats: dict[str, InitializationSpec]
    '''{format name ($...) or value keyword: InitializationSpec}'''
    operators: dict[str, Operator]
    '''{Operator name (NOT trigger): Operator}'''
    

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
