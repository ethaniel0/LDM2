from .parsing_types import *
import re


def parse_structure_into_components(structure: str) -> list[StructureComponent]:
    parts = re.split(r'\s+', structure)
    components: list[StructureComponent] = []
    for part in parts:
        if part.startswith('$') and not part.startswith('$$'):
            comp_type = StructureComponentType.Variable
            components.append(StructureComponent(comp_type, part[1:]))
        else:
            comp_type = StructureComponentType.String
            if part.startswith("$$"):
                part = part[1:]
            components.append(StructureComponent(comp_type, part))

    return components


def get_trigger(components: list[StructureComponent]) -> str:
    for comp in components:
        if comp.component_type == StructureComponentType.String:
            return comp.value
    return ""


def test_exprs_in_structure(components: list[StructureComponent]) -> bool:
    for comp in components:
        if comp.component_type == StructureComponentType.Variable:
            return True
    return False


def add_operator_def(spec: Spec, arg: dict):
    comp_name = arg['name']

    if comp_name not in spec.operators:
        raise ValueError(f"Operator {comp_name} not found")
    if len(spec.operators[comp_name].structure.component_defs) > 0:
        raise ValueError(f"Operator {comp_name} already has a definition")
    components = parse_structure_into_components(arg['structure'])

    trigger = get_trigger(components)
    if trigger == '':
        raise ValueError(f"Operator {comp_name} has no symbols")

    op = spec.operators[comp_name]
    op.structure.component_defs = components
    op.trigger = trigger
    op.precedence = arg['precedence']

    op.calc_num_variables()

    if not test_exprs_in_structure(components):
        raise ValueError(f"Operator {comp_name} must have at least one expression")

    op_left = components[0].component_type == StructureComponentType.Variable
    op_right = components[-1].component_type == StructureComponentType.Variable

    if op_left and op_right:
        op.operator_type = OperatorType.BINARY
    elif op_left:
        op.operator_type = OperatorType.UNARY_LEFT
    elif op_right:
        op.operator_type = OperatorType.UNARY_RIGHT
    else:
        op.operator_type = OperatorType.INTERNAL

    if 'associativity' not in arg:
        op.associativity = Associativity.LEFT_TO_RIGHT

    match arg['associativity']:
        case 'left-to-right':
            op.associativity = Associativity.LEFT_TO_RIGHT
        case 'right-to-left':
            op.associativity = Associativity.RIGHT_TO_LEFT
        case 'none':
            op.associativity = Associativity.NONE
        case _:
            raise ValueError(f"Unknown associativity {arg['associativity']}")


def add_value_keyword_def(spec: Spec, arg: dict):
    name = arg['name']
    typed_name = arg['typed_name']

    if name not in spec.initializer_formats:
        raise ValueError(f"Value Keyword {name} not found")

    value_type = spec.initializer_formats[name].ref_type
    if value_type == "":
        raise ValueError(f"Value Keyword {name} has no reference type")

    # replace the name with the typed name when being searched for
    init_format = spec.initializer_formats[name]
    del spec.initializer_formats[name]
    spec.initializer_formats[typed_name] = init_format



def add_keyword_def(spec: Spec, arg: dict):
    name = arg['name']
    components = parse_structure_into_components(arg['structure'])
    if name not in spec.keywords:
        raise ValueError(f"Keyword {name} not found")
    if len(spec.keywords[name].structure.component_defs) > 0:
        raise ValueError(f"Keyword {name} already has a definition")
    spec.keywords[name].structure.component_defs = components

    trigger = get_trigger(components)
    if trigger == '':
        raise ValueError(f"Keyword {name} has no symbols")

    spec.keywords[name].trigger = trigger


def add_structure_definitions_to_spec(spec: Spec, args: list[dict[str, str]]):
    for arg in args:
        comp_type = arg['type']
        comp_name = arg['name']

        match comp_type:
            case 'make_variable':
                if comp_name not in spec.make_variables:
                    raise ValueError(f"Make variable {comp_name} not found")
                if len(spec.make_variables[comp_name].structure.component_defs) > 0:
                    raise ValueError(f"Make variable {comp_name} already has a definition")
                components = parse_structure_into_components(arg['structure'])
                spec.make_variables[comp_name].structure.component_defs = components
                
            case 'operator':
                add_operator_def(spec, arg)

            case 'value_keyword':
                add_value_keyword_def(spec, arg)

            case 'keyword':
                add_keyword_def(spec, arg)

            case 'expression_separator':
                es = ExpressionSeparator(arg['name'], arg['value'])
                spec.expression_separators[arg['value']] = es

            case 'block':
                components = parse_structure_into_components(arg['structure'])
                spec.block_structures[arg['name']].structure.component_defs = components
                
            case _:
                raise ValueError(f"Unknown component type {comp_type}")
