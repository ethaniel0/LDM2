from .parsing_types import *
from typing import Any


def parse_method_argument(arg: dict[str, any]) -> MethodArgument:
    return MethodArgument(arg['name'], arg['type'], arg['optional'])


def parse_method(arg: dict[str, any]) -> Method:
    args = [parse_method_argument(a) for a in arg['arguments']]
    return Method(arg['name'], args, arg['returns'])


def parse_primitive_type_initialize(arg: dict[str, any]) -> PrimitiveTypeInitialize:
    return PrimitiveTypeInitialize(arg['type'])


def string_to_typespec(arg: str) -> TypeSpec:
    if '<' not in arg:
        return TypeSpec(arg, 0, [])
    if '>' not in arg:
        raise ValueError(f"Invalid type spec {arg}")
    inside_brackets = arg[arg.index('<') + 1:arg.rindex('>')].strip()
    # parse recursively, but allow for a list of types
    # can't just split "," because of nested types
    types = []
    start = 0
    depth = 0
    for i, c in enumerate(inside_brackets):
        if c == '<':
            depth += 1
        elif c == '>':
            depth -= 1
        elif c == ',' and depth == 0:
            types.append(string_to_typespec(inside_brackets[start:i].strip()))
            start = i + 1

    if start != len(inside_brackets):
        types.append(string_to_typespec(inside_brackets[start:].strip()))

    return TypeSpec(arg[:arg.index('<')], len(types), types)


def parse_primitive_type(arg: dict[str, Any]) -> PrimitiveType:
    methods = [parse_method(m) for m in arg['methods']]
    init = parse_primitive_type_initialize(arg['initialize'])
    if 'is' in arg and arg['is']:
        superclass = string_to_typespec(arg['is'])
    else:
        superclass = None
    typespec = TypeSpec(arg['name'], 0, [])
    return PrimitiveType(typespec, superclass, methods, init, [])


def parse_value_keyword(arg: dict[str, Any]) -> ValueKeyword:
    return ValueKeyword(arg['name'], arg['value_type'])


def parse_structure_component(arg: dict[str, Any]) -> StructureSpecComponent:
    other = {}

    base_type = ComponentType.UNKNOWN

    component_type_map = {
        'typename': ComponentType.TYPENAME,
        'name': ComponentType.NAME,
        'expression': ComponentType.EXPRESSION,
        'expressions': ComponentType.EXPRESSIONS,
        'block': ComponentType.BLOCK,
        'repeated_element': ComponentType.REPEATED_ELEMENT
    }

    for s, e in component_type_map.items():
        if arg['base'] == s:
            base_type = e
            break

    if base_type == ComponentType.UNKNOWN:
        raise ValueError(f"Unknown base type {arg['base']}")

    for k, v in arg.items():
        if k not in ['base', 'name']:
            if base_type == ComponentType.REPEATED_ELEMENT and k == 'components':
                other[k] = {c['name']: parse_structure_component(c) for c in v}
            else:
                other[k] = v

    if base_type == ComponentType.REPEATED_ELEMENT and 'components' not in other:
        raise ValueError(f"Repeated element {arg['name']} must have components")

    return StructureSpecComponent(base_type, arg['name'], other)


def parse_make_variable(arg: dict[str, Any]) -> StructuredObject:
    components = [parse_structure_component(c) for c in arg['components']]
    components = {c.name: c for c in components}
    return_type = '$type'
    var_name = '$varname'
    return StructuredObject(
        name=arg['name'],
        structure=Structure(components, []),
        value_type=string_to_typespec(return_type),
        value_name=var_name
    )


def build_type_tree(primitive_types: dict[str, PrimitiveType]) -> list[TypeTreeNode]:
    type_tree: dict[str, TypeTreeNode] = {}
    for key, val in primitive_types.items():
        type_tree[key] = TypeTreeNode(val, None, [])

    for pt in primitive_types.values():
        if pt.superclass:
            if pt.superclass.name not in type_tree:
                raise ValueError(f"Superclass {pt.superclass} not found for type {pt.spec.name}")
            type_tree[pt.superclass.name].children.append(type_tree[pt.spec.name])
            type_tree[pt.spec.name].parent = type_tree[pt.superclass.name]

    roots = [v for v in type_tree.values() if v.parent is None]
    return roots


def build_init_formats_from_type_tree(type_tree_roots: list[TypeTreeNode]) -> dict[str, InitializationSpec]:
    init_formats: dict[str, InitializationSpec] = {}
    q = []
    for root in type_tree_roots:
        is_var = root.type.initialize.type.startswith('$')
        if is_var:
            t = root.type.initialize.type
            init_formats[t] = InitializationSpec(root.type.spec.name,
                                                 InitializationType.VARIABLE,
                                                 root.type.initialize.type)
        q.extend([c for c in root.children])
    while len(q) > 0:
        node = q.pop()
        is_var = node.type.initialize.type.startswith('$')
        if is_var:
            t = node.type.initialize.type
            if t not in init_formats:
                init_formats[t] = InitializationSpec(node.type.spec.name,
                                                     InitializationType.VARIABLE,
                                                     node.type.initialize.type)
        q.extend([c for c in node.children])
    return init_formats


def parse_operator(arg: dict[str, Any]) -> Operator:
    name = arg['name']
    components = {}
    for item in arg['components']:
        s = StructureSpecComponent('operator_value', item['name'], {})
        components[item['name']] = s
    structure = Structure(components, [])
    return Operator(name, 0, structure, [], "", Associativity.NONE)


def parse_operator_overload(arg: dict[str, Any]) -> OperatorOverload:
    name: str = arg['name']
    return_type: str = arg['return']
    return_typespec = string_to_typespec(return_type)
    other: dict[str, TypeSpec] = {}
    for i in arg.keys():
        if i != 'name' and i != 'return' and i != 'type':
            other[i] = string_to_typespec(arg[i])
    
    return OperatorOverload(name, return_typespec, other)


def parse_keyword(arg: dict[str, Any]) -> StructuredObject:
    name = arg['name']
    components = [parse_structure_component(c) for c in arg['components']]
    components = {c.name: c for c in components}
    structure = Structure(components, [])

    return StructuredObject(
        name=name,
        structure=structure,
        value_type=None,
        value_name=None
    )


def parse_make_object(arg: dict[str, Any]) -> StructuredObject:
    name = arg['name']
    components = [parse_structure_component(c) for c in arg['components']]
    components = {c.name: c for c in components}
    structure = Structure(components, [])
    return StructuredObject(
        name=name,
        structure=structure,
        value_type=string_to_typespec(arg['value_type']),
        value_name="$varname"
    )


def parse_spec(arg: list[dict[str, Any]]) -> Spec:
    primitive_types: dict[str, PrimitiveType] = {}
    structured_objects: dict[str, StructuredObject] = {}
    operators: dict[str, Operator] = {}
    operator_overloads: list[OperatorOverload] = []
    expression_separators: dict[str, ExpressionSeparator] = {}
    block_structures: dict[str, BlockStructure] = {}

    for item in arg:
        match item['type']:
            case 'primitive_type':
                pt = parse_primitive_type(item)
                primitive_types[item['name']] = pt

            case 'value_keyword':
                vk = parse_value_keyword(item)
                if vk.value_type not in primitive_types:
                    raise ValueError(f"Value type {vk.value_type} not found")
                primitive_types[vk.value_type].value_keywords.append(vk)

            case 'make_variable':
                name = item['name']
                if name in structured_objects:
                    raise ValueError(f"Object {name} already exists")
                structured_objects[name] = parse_make_variable(item)

            case 'make_object':
                name = item['name']
                if name in structured_objects:
                    raise ValueError(f"Object {name} already exists")
                structured_objects[name] = parse_make_object(item)

            case 'keyword':
                name = item['name']
                if name in structured_objects:
                    raise ValueError(f"Keyword {name} already exists")
                structured_objects[name] = parse_keyword(item)
                
            case 'operator':
                operators[item['name']] = parse_operator(item)
            
            case 'operator_overload':
                operator_overloads.append(parse_operator_overload(item))



            case 'block':
                spec_components = {}
                for c in item['components']:
                    spec_components[c['name']] = parse_structure_component(c)
                b = BlockStructure(item['name'], Structure(spec_components, []))
                block_structures[item['name']] = b

            case _:
                raise ValueError(f"Unknown type {item['type']}")
    
    for overload in operator_overloads:
        if overload.name not in operators:
            raise ValueError(f'type {overload.name} does not exist for overload to connect to')
        op = operators[overload.name]
        if not op.overload_matches(overload):
            raise ValueError(f'operator overload {overload} does not match operator structure for operator {op.name}')
        op.overloads.append(overload)        

    # build type tree
    type_tree_roots = build_type_tree(primitive_types)
    init_formats = build_init_formats_from_type_tree(type_tree_roots)

    for pt in primitive_types.values():
        if len(pt.value_keywords) == 0:
            continue
        for keyword in pt.value_keywords:
            if keyword.name in init_formats:
                raise ValueError(f"Value keyword {keyword.name} already exists")
            init_formats[keyword.name] = InitializationSpec(keyword.value_type,
                                                            InitializationType.LITERAL,
                                                            keyword.name)

    return Spec(
        primitive_types=primitive_types,
        structured_objects=structured_objects,
        initializer_formats=init_formats,
        operators=operators,
        expression_separators=expression_separators,
        block_structures=block_structures
    )
