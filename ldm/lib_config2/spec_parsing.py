from .parsing_types import *


def parse_method_argument(arg: dict[str, any]) -> MethodArgument:
    return MethodArgument(arg['name'], arg['type'], arg['optional'])


def parse_method(arg: dict[str, any]) -> Method:
    args = [parse_method_argument(a) for a in arg['arguments']]
    return Method(arg['name'], args, arg['returns'])


def parse_primitive_type_initialize(arg: dict[str, any]) -> PrimitiveTypeInitialize:
    return PrimitiveTypeInitialize(arg['type'])


def parse_primitive_type(arg: dict[str, any]) -> PrimitiveType:
    methods = [parse_method(m) for m in arg['methods']]
    init = parse_primitive_type_initialize(arg['initialize'])
    superclass = arg['is']
    return PrimitiveType(arg['name'], methods, init, [], superclass)


def parse_value_keyword(arg: dict[str, any]) -> ValueKeyword:
    return ValueKeyword(arg['name'], arg['value_type'])


def parse_structure_component(arg: dict[str, any]) -> StructureSpecComponent:
    other = {}
    for k, v in arg.items():
        if k not in ['base', 'name']:
            other[k] = v
    return StructureSpecComponent(arg['base'], arg['name'], other)


def parse_make_variable(arg: dict[str, any]) -> MakeVariable:
    components = [parse_structure_component(c) for c in arg['components']]
    components = {c.name: c for c in components}
    return MakeVariable(arg['name'], Structure(components, []))


def build_type_tree(primitive_types: dict[str, PrimitiveType]) -> list[TypeTreeNode]:
    type_tree: dict[str, TypeTreeNode] = {}
    for key, val in primitive_types.items():
        type_tree[key] = TypeTreeNode(val, None, [])

    for pt in primitive_types.values():
        if pt.superclass:
            if pt.superclass not in type_tree:
                raise ValueError(f"Superclass {pt.superclass} not found for type {pt.name}")
            type_tree[pt.superclass].children.append(type_tree[pt.name])
            type_tree[pt.name].parent = type_tree[pt.superclass]

    roots = [v for v in type_tree.values() if v.parent is None]
    return roots


def build_init_formats_from_type_tree(type_tree_roots: list[TypeTreeNode]) -> dict[str, InitializationSpec]:
    init_formats: dict[str, InitializationSpec] = {}
    q = []
    for root in type_tree_roots:
        is_var = root.type.initialize.type.startswith('$')
        if is_var:
            t = root.type.initialize.type
            init_formats[t] = InitializationSpec(root.type.name,
                                                 InitializationType.VARIABLE,
                                                 root.type.initialize.type)
        q.extend([c for c in root.children])
    while len(q) == 0:
        node = q.pop()
        is_var = node.type.initialize.type.startswith('$')
        if is_var:
            t = node.type.initialize.type
            if t not in init_formats:
                init_formats[t] = InitializationSpec(node.type.name,
                                                     InitializationType.VARIABLE,
                                                     node.type.initialize.type)
        q.extend([c for c in node.children])
    return init_formats


def parse_operator(arg: dict[str, any]) -> Operator:
    name = arg['name']
    precedence = arg['precedence']
    components = {}
    for item in arg['components']:
        s = StructureSpecComponent('operator_value', item['name'], {})
        components[item['name']] = s
    structure = Structure(components, [])
    return Operator(name, precedence, structure, [], "", Associativity.NONE)


def parse_operator_overload(arg: dict[str, any]) -> OperatorOverload:
    name = arg['name']
    return_type = arg['return']
    other = {}
    for i in arg.keys():
        if i != 'name' and i != 'return' and i != 'type':
            other[i] = arg[i]
    
    return OperatorOverload(name, return_type, other)


def parse_spec(arg: list[dict[str, any]]) -> Spec:
    primitive_types: dict[str, PrimitiveType] = {}
    make_variables: dict[str, MakeVariable] = {}
    operators: dict[str, Operator] = {}
    operator_overloads: list[OperatorOverload] = []

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
                make_variables[item['name']] = parse_make_variable(item)
                
            case 'operator':
                operators[item['name']] = parse_operator(item)
            
            case 'operator_overload':
                operator_overloads.append(parse_operator_overload(item))

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

    return Spec(primitive_types, make_variables, init_formats, operators)
