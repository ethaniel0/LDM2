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

    def __eq__(self, other):
        if not isinstance(other, TypeSpec):
            return False
        if self.name != other.name or self.num_subtypes != other.num_subtypes:
            return False

        for i in range(self.num_subtypes):
            if self.subtypes[i] != other.subtypes[i]:
                return False

        return True


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


class OperatorType(Enum):
    UNKNOWN = 0
    '''Unknown operator type. Used as an initializer, will error if propagated to code parsing.'''

    BINARY = 1
    '''Binary operator that takes an expression on the left and right. 
    Also includes the ternary operator or any operator with an expression in the middle'''

    UNARY_RIGHT = 2
    '''Unary operator that takes an expression on the right, as the negation operator:
     
    x = -some_number.
     
    Also includes operators that contain multiple expressions prepended by a unary operator as such:
    
    (+ a b) to signal a + b '''

    UNARY_LEFT = 3
    '''Unary operator that takes an expression on the left, as the increment operator:
    
    x = ++some_number.
    
    Also includes operators that contain multiple expressions appended by a unary operator as such:
    
    (a b +) to signal a + b
    '''

    INTERNAL = 4
    '''Internal operator that does not expose any expressions on the right or left, such as parentheses.'''


@dataclass
class Operator:
    name: str
    '''The name of the operator. Is only used for bookkeeping, not for parsing.'''
    precedence: int
    '''The precedence of the operator. Lower precedence hugs values more closely.'''
    structure: Structure
    '''The structure of the operator. Contains the components and their definitions.'''
    overloads: list[OperatorOverload]
    '''The overloads of the operator. Contains the return type and the types of the variables 
    for each combination of types'''
    trigger: str
    '''The trigger of the operator. Once found, the operator is created and structure parsed'''
    associativity: Associativity
    '''The associativity of the operator. Determines how the operator is parsed in the absence of parentheses'''
    operator_type: OperatorType = OperatorType.UNKNOWN
    '''The type of the operator (binary, unary, internal). Is determined by the structure of the operator.'''
    num_variables: int = 0

    def __init__(self, name: str, precedence: int, structure: Structure, overloads: list[OperatorOverload],
                 trigger: str, associativity: Associativity):
        self.name = name
        self.precedence = precedence
        self.structure = structure
        self.overloads = overloads
        self.trigger = trigger
        self.associativity = associativity
        self.operator_type = OperatorType.UNKNOWN
        self.num_variables = 0

    def calc_num_variables(self):
        for i in self.structure.component_defs:
            if i.component_type == StructureComponentType.Variable:
                self.num_variables += 1


    def overload_matches(self, overload: OperatorOverload):
        """Checks if an overload configuration matches the operator structure"""
        # Get all variable names from structure components
        structure_vars = set()
        for comp in self.structure.component_specs.values():
            if comp.base == "operator_value":
                structure_vars.add(comp.name)
        
        overload_vars = set(overload.variables.keys())
                
        # Check if all variables in overload exist in structure
        return structure_vars == overload_vars


@dataclass
class Keyword:
    name: str
    '''The name of the keyword. Is only used for bookkeeping, not for parsing.'''
    structure: Structure
    '''The structure of the keyword. Contains the components and their definitions.'''
    trigger: str
    '''The trigger of the keyword. Once found, the keyword is created and structure parsed'''


@dataclass
class ExpressionSeparator:
    name: str
    value: str


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
    keywords: dict[str, Keyword]
    '''{Keyword name: Keyword}'''
    expression_separators: dict[str, ExpressionSeparator]
    '''{ExpressionSeparator name: ExpressionSeparator}'''
    

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
    '''Name of the type it maps to. ex: true to bool'''
    init_type: InitializationType
    '''Initialization type. Variable or literal'''
    format: str
    '''Format of the initialization. ex: $int or true'''


@dataclass
class TypeTreeNode:
    type: PrimitiveType
    parent: TypeTreeNode | None
    children: list[TypeTreeNode]
