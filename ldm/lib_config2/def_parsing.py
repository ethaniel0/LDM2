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
                if comp_name not in spec.operators:
                    raise ValueError(f"Operator {comp_name} not found")
                if len(spec.operators[comp_name].structure.component_defs) > 0:
                    raise ValueError(f"Operator {comp_name} already has a definition")
                if 'trigger' not in arg:
                    raise ValueError(f"Operator {comp_name} missing required 'trigger' field")
                components = parse_structure_into_components(arg['structure'])

                op = spec.operators[comp_name]
                op.structure.component_defs = components
                op.trigger = arg['trigger']

                if 'associativity' not in arg:
                    raise ValueError(f"Operator {comp_name} missing required 'associativity' field")

                match arg['associativity']:
                    case 'left-to-right':
                        op.associativity = Associativity.LEFT_TO_RIGHT
                    case 'right-to-left':
                        op.associativity = Associativity.RIGHT_TO_LEFT
                    case 'none':
                        op.associativity = Associativity.NONE
                    case _:
                        raise ValueError(f"Unknown associativity {arg['associativity']} for operator {comp_name}")

                
            case _:
                raise ValueError(f"Unknown component type {comp_type}")