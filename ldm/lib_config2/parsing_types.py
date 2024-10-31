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
class OperatorOverload:
    name: str
    return_type: str
    variables: dict[str, str]
    
    def __str__(self):
        return f"<{self.name}|{self.variables.values()}>"
    
    
@dataclass
class Operator:
    name: str
    precedence: int
    structure: Structure
    overloads: list[OperatorOverload]
    
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
    make_variables: dict[str, MakeVariable]
    initializer_formats: dict[str, InitializationSpec]
    operators: dict[str, Operator]
    


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

