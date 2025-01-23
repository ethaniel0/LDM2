from ldm.ast.parsing_types import ParsingItems, ValueToken, StructuredObjectInstance, ParsingContext, NameInstance, \
    TypenameInstance
from ldm.lib_config2.parsing_types import TypeSpec, ComponentType, ConfigTypeSpec


def typespec_matches(t1: TypeSpec, t2: TypeSpec) -> bool:
    if t1.name != t2.name:
        return False
    if t1.num_subtypes != t2.num_subtypes:
        return False
    if t1.associated_structure is not None and t2.associated_structure is not None:
        if t1.associated_structure.name != t2.associated_structure.name:
            return False
    elif t1.associated_structure != t2.associated_structure:
            return False
    if t1.num_subtypes == 0:
        return True
    for i in range(t1.num_subtypes):
        if not typespec_matches(t1.subtypes[i], t2.subtypes[i]):
            return False
    return True

def extract_generics(overload_type: ConfigTypeSpec, actual_type: TypeSpec, op: StructuredObjectInstance, parsing_context: ParsingContext) -> dict[str, TypeSpec] | None:
    if isinstance(actual_type, list) and not overload_type.name.startswith('$typename_attributes'):
        return None

    generics_map = {}

    if overload_type.name == '$typename':
        overload_type = overload_type.subtypes[0]
        generic_name = overload_type.name
        if generic_name in generics_map:
            if not typespec_matches(generics_map[generic_name], actual_type):
                return None
        else:
            generics_map[generic_name] = actual_type
    elif overload_type.name == '$typename_attributes':
        overload_inner_type = overload_type.subtypes[0]
        item = op.extract_from_path(overload_inner_type.name)
        if len(item) != 1:
            return None
        item = item[0]
        item_type = parsing_context.variables[item.value.value]
        path_parts = overload_type.path.split('.')
        for part in path_parts:
            if part not in item_type.attributes:
                return None
            item_type = item_type.attributes[part]

        if isinstance(actual_type, list):
            if not isinstance(item_type, list) or len(item_type) != len(actual_type):
                return None
            for i in range(len(actual_type)):
                if not typespec_matches(item_type[i], actual_type[i]):
                    return None
            return generics_map

        else:
            if not typespec_matches(item_type, actual_type):
                return None
            return generics_map

    elif overload_type.name == '$typename_attributes_map_full':
        overload_inner_type = overload_type.subtypes[0]
        item = op.extract_from_path(overload_inner_type.name)
        if len(item) != 1:
            return None
        item = item[0]
        item_type = parsing_context.variables[item.value.name]

        keys: list[NameInstance] = op.extract_from_path(overload_type.path)

        keys_types = []

        if len(keys) != len(item_type.attributes):
            return None

        for key in keys:
            if key.value not in item_type.attributes:
                return None
            keys_types.append(item_type.attributes[key.value])

        if not isinstance(actual_type, list) or len(actual_type) != len(keys_types):
            return None

        return generics_map

    else:
        if overload_type.name != actual_type.name:
            return None

    if len(overload_type.subtypes) != len(actual_type.subtypes):
        return None
    for i in range(len(overload_type.subtypes)):
        g = extract_generics(overload_type.subtypes[i], actual_type.subtypes[i], op, parsing_context)
        if g is None:
            return None
        for key in g.keys():
            if key in generics_map:
                if not typespec_matches(generics_map[key], g[key]):
                    return None
            else:
                generics_map[key] = g[key]

    return generics_map

def type_operator(op: StructuredObjectInstance, parsing_items: ParsingItems, parsing_context: ParsingContext):
    types: dict[str, TypeSpec | list[TypeSpec]] = {}

    var_components = op.so.create_operator.fields

    for i, val_name in enumerate(var_components):
        if '.' in val_name:
            comp = op.extract_from_path(val_name)
        else:
            comp = op.components[val_name]
        if isinstance(comp, StructuredObjectInstance):
            type_operator(comp, parsing_items, parsing_context)
            types[val_name] = comp.operator_fields.result_type
        elif isinstance(comp, ValueToken):
            types[val_name] = comp.var_type
        elif isinstance(comp, TypenameInstance):
            types[val_name] = comp.value
        elif isinstance(comp, list):
            nested_types = []
            for item in comp:
                if isinstance(item, StructuredObjectInstance):
                    type_operator(item, parsing_items, parsing_context)
                    nested_types.append(item.operator_fields.result_type)
                elif isinstance(item, ValueToken):
                    nested_types.append(item.var_type)
                else:
                    raise ValueError(f"Unexpected component type {item}")
            types[val_name] = nested_types

        else:
            raise ValueError(f"Unexpected component type {comp}")

    generics_map = {}

    for overload in op.so.create_operator.overloads:
        if len(overload.variables) != len(types):
            continue

        works = True
        for key in types.keys():
            v = types[key]
            g = extract_generics(overload.variables[key], v, op, parsing_context)
            if g is None:
                works = False
                break
            for key in g.keys():
                if key in generics_map:
                    if not typespec_matches(generics_map[key], g[key]):
                        works = False
                        break
                else:
                    generics_map[key] = g[key]

        if works:
            if overload.return_type.name == '$typename':
                op.operator_fields.result_type = generics_map[overload.return_type.subtypes[0].name]
            elif overload.return_type.name == '$typename_field':
                inner_type = overload.return_type.subtypes[0]
                path = overload.return_type.path.split('.')
                item = op.extract_from_path(inner_type.name)
                if len(item) != 1:
                    raise ValueError(f"Could not find item {inner_type.name[1:]}")
                item = item[0]
                item_type = parsing_context.variables[item.value.value]

                for part in path:
                    if part.startswith('$'):
                        items = op.extract_from_path(part)
                        if len(items) != 1:
                            raise ValueError(f"Could not find item {part}")
                        item = items[0]
                        part = item.value
                    if part not in item_type.attributes:
                        raise ValueError(f"Could not find attribute {part}")
                    item_type = item_type.attributes[part]
                op.operator_fields.result_type = item_type
            else:
                op.operator_fields.result_type = overload.return_type
            return

    raise ValueError(f"No overload found for operator {op.so.name} with types {types}")


