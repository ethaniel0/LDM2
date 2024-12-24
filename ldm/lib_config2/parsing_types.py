from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Any


# SPECS
@dataclass
class TypeSpec:
    name: str
    '''name of the type'''
    num_subtypes: int
    '''number of subtypes'''
    subtypes: list[TypeSpec]
    '''list of subtypes'''
    attributes: dict[str, TypeSpec]
    def __init__(self, name: str, num_subtypes: int, subtypes: list[TypeSpec], attributes=None):
        self.name = name
        self.num_subtypes = num_subtypes
        self.subtypes = subtypes
        self.attributes = attributes or {}

    def __eq__(self, other):
        if not isinstance(other, TypeSpec):
            return False
        if self.name != other.name or self.num_subtypes != other.num_subtypes:
            return False

        for i in range(self.num_subtypes):
            if self.subtypes[i] != other.subtypes[i]:
                return False

        if set(self.attributes.keys()) != set(other.attributes.keys()):
            return False

        for key, value in self.attributes.items():
            if value != other.attributes[key]:
                return False

        return True

    def __str__(self):
        return f"{self.name}{'<' + ', '.join([str(i) for i in self.subtypes]) + '>' if self.num_subtypes > 0 else ''}"

    def __repr__(self):
        return str(self)


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
class StructureComponent:
    component_type: StructureComponentType
    value: str
    inner_structure: list[StructureComponent] | None = None
    inner_fields: dict[str, str] | None = None


class ComponentType(Enum):
    UNKNOWN = None
    TYPENAME = 'typename'
    NAME = 'name'
    EXPRESSION = 'expression'
    EXPRESSIONS = 'expressions',
    REPEATED_ELEMENT = 'repeated_element',
    STRUCTURE = 'structure',
    OPERATOR_VALUE = 'operator_value'


@dataclass
class StructureSpecComponent:
    base: ComponentType
    '''Spec component type: typename, name, expression, etc.'''
    name: str
    '''Transpiler-internal variable name associated with the component. Used to find the component during translation.'''
    other: dict[str, Any]
    '''Other internal variables used for compiling structure components. These are structure specific.
    
    typename: no other components.
    
    name:
        type: "existing-global", "new-global", "existing-local", "new-local", "any"
    
    repeated_element:
        components: list with more StructureSpecComponents
    '''


@dataclass
class Structure:
    component_specs: dict[str, StructureSpecComponent]
    component_defs: list[StructureComponent]

#### STRUCTURED OBJECTS ####

class ScopeOptions(Enum):
    LOCAL = 'local'
    GLOBAL = 'global'

@dataclass
class CreateVariable:
    """
    Components defining how a StructuredObject creates a value (variable).
    This registers a value as a variable *inside the parser* with a given name and type.
    Using this does not mean that the structure has a return type of the type.
    """
    name: str
    """The name of the component"""
    type: TypeSpec
    """The type of the component it creates"""
    scope: ScopeOptions
    """The scope of the component: local or global"""
    check_type: str | None
    """The value / expression to check to make sure the typing is correct"""
    attributes: dict[str, TypeSpec] | None = None

@dataclass
class CreateType:
    """
    Components defining how a StructuredObject creates a type. It makes this component available
    as a type in the selected scope.
    """
    type: TypeSpec
    """The typespec for the type the component creates"""
    scope: ScopeOptions
    """The scope of the component: local or global"""
    fields_containers: list[str] | None = None
    """Variables inside which created variables and types are added to that type's field list."""

@dataclass
class OperatorOverload:
    name: str
    return_type: TypeSpec
    variables: dict[str, TypeSpec]

    def __str__(self):
        return f"<{self.name}|{self.variables.values()}>"

class Associativity(Enum):
    LEFT_TO_RIGHT = 0
    RIGHT_TO_LEFT = 1
    NONE = 2

@dataclass
class CreateOperator:
    fields: list[str]
    '''The fields in the operator's structure that are adjusted for each overload / used to determine the output type'''

    precedence: int
    '''The precedence of the operator. Lower precedence hugs values more closely.'''

    associativity: Associativity
    '''The associativity of the operator. Determines how the operator is parsed in the absence of parentheses'''

    overloads: list[OperatorOverload]
    '''The overloads of the operator. Contains the return type and the types of the variables 
    for each combination of types'''

    def overload_matches(self, overload: OperatorOverload):
        """Checks if an overload configuration matches the operator structure"""
        # Get all variable names from structure components
        structure_vars = set(self.fields)
        overload_vars = set(overload.variables.keys())

        # Check if all variables in overload exist in structure
        return structure_vars == overload_vars

@dataclass
class StructuredObject:
    name: str
    '''Structure name. Used only to keep track of each structure.'''
    structure: Structure
    '''The corresponding structure'''
    create_variable: CreateVariable | None = None
    '''If the structure adds a variable to the parser, this is defined.'''
    create_type: CreateType | None = None
    '''If the structure adds a type to the parser, this is defined.'''
    create_operator: CreateOperator | None = None
    '''If the structure acts as an operator, this is defined.'''
    dependent: bool | None = False
    '''
    When false, can be used independently of other structures.
    When true, can only be called upon when being parsed as part of another structure.
    '''

    def get_nth_component(self, n: int):
        defs = self.structure.component_defs
        def_vars: list[StructureComponent] = list(
            filter(lambda v: v.component_type == StructureComponentType.Variable, defs)
        )
        sc = def_vars[n]
        return self.structure.component_specs[sc.value]

#### STRUCTURE FILTERS ####

class StructureFilterComponentType(Enum):
    AND = "and"
    STRUCTURE = "structure"
    CONTAINS = "contains"
    EXCLUDES = "excludes",

@dataclass
class StructureFilterComponent:
    type: StructureFilterComponentType
    value: str | list[StructureFilterComponent]

    def matches(self, structure: StructuredObject) -> bool:
        if  self.type == StructureFilterComponentType.AND:
            for item in self.value:
                if not item.matches(structure):
                    return False
            return True

        elif self.type == StructureFilterComponentType.STRUCTURE:
            return structure.name == self.value

        elif self.type == StructureFilterComponentType.CONTAINS:
            match self.value:
                case "create_variable":
                    return structure.create_variable is not None
                case "create_type":
                    return structure.create_type is not None
                case _:
                    raise RuntimeError(f"Structure filter does not support contains query for {self.value}")

        elif self.type == StructureFilterComponentType.EXCLUDES:
            match self.value:
                case "create_variable":
                    return structure.create_variable is None
                case "create_type":
                    return structure.create_type is None
                case _:
                    raise RuntimeError(f"Structure filter does not support excludes query for {self.value}")


@dataclass()
class StructureFilter:
    all: bool
    allow_expressions: bool
    filters: list[StructureFilterComponent]
    def __init__(self, all_allowed: bool=False, allow_expressions: bool=False, filters: list[StructureFilterComponent]=None):
        self.all = all_allowed
        self.allow_expressions = allow_expressions
        self.filters = filters or []

    def matches(self, structure: StructuredObject) -> bool:
        if self.all:
            return True
        if self.allow_expressions and len(self.filters) == 0:
            return False
        for f in self.filters:
            if not f.matches(structure):
                return False
        return True


#### TYPES ####

@dataclass
class FieldItem:
    name: str
    type: TypeSpec
    optional: bool

@dataclass
class GeneralType(Protocol):
    """Protocol used to define the structure for a PrimitiveType and a UserDefinedType"""
    spec: TypeSpec
    superclass: TypeSpec | None
    fields: dict[str, TypeSpec]


@dataclass
class PrimitiveTypeInitialize:
    type: str

@dataclass
class PrimitiveType:
    spec: TypeSpec
    '''TypeSpec of the primitive type'''
    superclass: TypeSpec | None
    '''Superclass of the primitive type'''
    initialize: PrimitiveTypeInitialize
    value_keywords: list[ValueKeyword]


@dataclass
class UserDefinedType:
    spec: TypeSpec
    superclass: TypeSpec | None
    structure: Structure


#### OPERATORS ####

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
            if comp.base == ComponentType.OPERATOR_VALUE:
                structure_vars.add(comp.name)

        overload_vars = set(overload.variables.keys())

        # Check if all variables in overload exist in structure
        return structure_vars == overload_vars

#### OTHER: EXPRESSION SEPARATORS ####

@dataclass
class ExpressionSeparator:
    name: str
    value: str

@dataclass
class Spec:
    primitive_types: dict[str, PrimitiveType]
    '''{typename: PrimitiveType}'''
    structured_objects: dict[str, StructuredObject]
    '''{StructuredObject name: StructuredObject}'''
    initializer_formats: dict[str, InitializationSpec]
    '''{format name ($...) or value keyword: InitializationSpec}'''
    operators: dict[str, Operator]
    '''{Operator name (NOT trigger): Operator}'''
    expression_separators: dict[str, ExpressionSeparator]
    

# DEFINITIONS
class StructureComponentType(Enum):
    String = 1
    Variable = 2
    Command = 3
    EndCommand = 4


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
