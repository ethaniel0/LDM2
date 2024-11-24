from ldm.ast.parsing_types import OperatorInstance, ParsingItems, ValueToken
from ldm.lib_config2.parsing_types import TypeSpec, StructureComponentType


def typespec_matches(t1: TypeSpec, t2: TypeSpec) -> bool:
    if t1.name != t2.name:
        return False
    if t1.num_subtypes != t2.num_subtypes:
        return False
    if t1.num_subtypes == 0:
        return True
    for i in range(t1.num_subtypes):
        if not typespec_matches(t1.subtypes[i], t2.subtypes[i]):
            return False
    return True


def type_operator(op: OperatorInstance, parsing_items: ParsingItems):
    types: dict[str, TypeSpec] = {}

    var_components = [d for d in op.operator.structure.component_defs
                      if d.component_type == StructureComponentType.Variable]

    for i, comp in enumerate(op.operands):
        val_name = var_components[i].value
        if isinstance(comp, OperatorInstance):
            type_operator(comp, parsing_items)
            types[val_name] = comp.result_type
        elif isinstance(comp, ValueToken):
            types[val_name] = comp.var_type

    generics_map = {}

    for overload in op.operator.overloads:
        if len(overload.variables) != len(types):
            continue

        works = True
        for key in types.keys():
            v = types[key]
            if overload.variables[key].name == '$typename':
                generic_name = overload.variables[key].name
                if generic_name in generics_map:
                    if not typespec_matches(generics_map[generic_name], v):
                        works = False
                        break
                else:
                    generics_map[generic_name] = v
            else:
                if not typespec_matches(v, overload.variables[key]):
                    works = False
                    break

        if works:
            if overload.return_type.name == '$typename':
                op.result_type = generics_map[overload.return_type.name]
            else:
                op.result_type = overload.return_type
            return

    raise ValueError(f"No overload found for operator {op.operator.name} with types {types}")


