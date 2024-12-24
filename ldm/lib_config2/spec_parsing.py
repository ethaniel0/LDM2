from .parsing_types import *
from typing import Any


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
    init = parse_primitive_type_initialize(arg['initialize'])
    if 'is' in arg and arg['is']:
        superclass = string_to_typespec(arg['is'])
    else:
        superclass = None
    typespec = TypeSpec(arg['name'], 0, [])
    return PrimitiveType(typespec, superclass, init, [])


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
        'repeated_element': ComponentType.REPEATED_ELEMENT,
        'structure': ComponentType.STRUCTURE,
    }

    # assigns base_type to be one of the ComponentTypes based on the string type in the json
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
        s = StructureSpecComponent(ComponentType.OPERATOR_VALUE, item['name'], {})
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

def get_create_variable(arg: dict[str, Any]) -> CreateVariable | None:

    if 'create_variable' not in arg:
        return None

    scope_options = {
        'local': ScopeOptions.LOCAL,
        'global': ScopeOptions.GLOBAL,
    }

    cv = arg['create_variable']

    if 'name' not in cv:
        raise ValueError(f"create_variable {cv} must have name specified")
    if 'type' not in cv:
        raise ValueError(f"create_variable {cv} must have type specified")
    if 'scope' not in cv:
        raise ValueError(f"create_variable {cv} must have scope specified")
    check_type = None
    if 'check_type' in cv:
        check_type = cv['check_type']

    val_name = cv['name']
    val_type = string_to_typespec(cv['type'])
    if cv['scope'] not in scope_options:
        raise ValueError('Scope must be one of local, global')
    val_scope = scope_options[cv['scope']]
    return CreateVariable(val_name, val_type, val_scope, check_type)

def get_create_type(arg: dict[str, Any]) -> CreateType | None:
    if 'create_type' not in arg:
        return None

    scope_options = {
        'local': ScopeOptions.LOCAL,
        'global': ScopeOptions.GLOBAL,
    }

    ct = arg['create_type']
    if 'type' not in ct:
        raise ValueError(f"create_type {ct} must have type specified")
    if 'scope' not in ct:
        raise ValueError(f"create_type {ct} must have scope specified")
    if 'fields_containers' not in ct:
        raise ValueError(f"create_type {ct} must have fields_containers specified")

    val_type = string_to_typespec(ct['type'])

    if ct['scope'] not in scope_options:
        raise ValueError('Scope must be one of local, global')
    val_scope = scope_options[ct['scope']]

    val_fields = ct['fields_containers']

    return CreateType(val_type, val_scope, val_fields)

def get_create_operator(arg: dict[str, Any]) -> CreateOperator | None:
    if not 'create_operator' in arg:
        return None

    co = arg['create_operator']
    if not 'overload_fields' in co:
        raise ValueError(f"create_operator {co} must specify overload_fields")

    return CreateOperator(co['overload_fields'], 0, Associativity.NONE, [])

def parse_general_structure(arg: dict[str, Any]) -> StructuredObject:
    name = arg['name']
    components = [parse_structure_component(c) for c in arg['components']]
    components = {c.name: c for c in components}
    structure = Structure(components, [])

    create_variable = get_create_variable(arg)
    create_type = get_create_type(arg)
    create_operator = get_create_operator(arg)

    is_dependent = False

    if 'dependent' in arg and arg['dependent']:
        is_dependent = True

    return StructuredObject(
        name=name,
        structure=structure,
        create_variable=create_variable,
        create_type=create_type,
        create_operator=create_operator,
        dependent=is_dependent,
    )


def parse_spec(arg: list[dict[str, Any]]) -> Spec:
    primitive_types: dict[str, PrimitiveType] = {}
    structured_objects: dict[str, StructuredObject] = {}
    operators: dict[str, Operator] = {}
    operator_overloads: list[OperatorOverload] = []
    expression_separators: dict[str, ExpressionSeparator] = {}

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

            case "structure":
                name = item['name']
                if name in structured_objects:
                    raise ValueError(f"Object {name} already exists")
                structured_objects[name] = parse_general_structure(item)
                
            case 'operator':
                operators[item['name']] = parse_operator(item)
            
            case 'operator_overload':
                operator_overloads.append(parse_operator_overload(item))

            case _:
                raise ValueError(f"Unknown type {item['type']}")
    
    for overload in operator_overloads:
        if overload.name not in structured_objects:
            raise ValueError(f'type {overload.name} does not exist for overload to connect to')
        op = structured_objects[overload.name]
        if not op.create_operator:
            raise ValueError(f"Structure {overload.name} is not an operatorx")
        if not op.create_operator.overload_matches(overload):
            raise ValueError(f'operator overload {overload} does not match operator structure for operator {op.name}')
        op.create_operator.overloads.append(overload)

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
    )

