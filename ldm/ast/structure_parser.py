from __future__ import annotations

from typing import Any

from ldm.ast.type_checking import typespec_matches
from ldm.lib_config2.spec_parsing import string_to_typespec
from ldm.source_tokenizer.tokenize import Token, TokenizerItems, Tokenizer
from ldm.ast.parsing_types import (TokenIterator, ParsingItems, ParsingContext,
                                   OperatorInstance, ValueToken,
                                   StructuredObjectInstance, NameInstance, TypenameInstance, SOInstanceItem)
from ldm.lib_config2.parsing_types import Structure, StructureComponentType, StructureComponent, TypeSpec, \
    ComponentType, StructureFilter, StructureFilterComponent, StructureFilterComponentType, StructureSpecComponent
from ldm.ast.expression_parser import ExpressionParser

def to_typespec(token: Token) -> TypeSpec:
    return TypeSpec(token.value, 0, [])

def to_filter(filter_list: list[dict] | str) -> StructureFilter:
    if filter_list == 'all':
        return StructureFilter(all_allowed=True, allow_expressions=True)
    if filter_list == 'expressions':
        return StructureFilter(allow_expressions=True)

    filter = StructureFilter()

    for item in filter_list:
        if item['type'] == 'contains':
            filter.filters.append(
                StructureFilterComponent(
                    StructureFilterComponentType.CONTAINS,
                    item['contains']
                )
            )
        elif item['type'] == 'excludes':
            filter.filters.append(
                StructureFilterComponent(
                    StructureFilterComponentType.EXCLUDES,
                    item['excludes']
                )
            )
        elif item['type'] == 'structure':
            filter.filters.append(
                StructureFilterComponent(
                    StructureFilterComponentType.STRUCTURE,
                    item['structure']
                )
            )
        elif item['type'] == 'and':
            filter.filters.append(
                StructureFilterComponent(
                    StructureFilterComponentType.AND,
                    to_filter(item['filters']).filters
                )
            )
        elif item['type'] == 'expression':
            if item['allow'] not in [True, False]:
                raise ValueError(f'Invalid allow type: {item["allow"]}')
            filter.allow_expressions = item['allow']

    return filter

def check_valid_type(typespec: TypeSpec, items: ParsingItems, context: ParsingContext, exclude: str="") -> bool:
    name = typespec.name

    found = False

    if name in items.config_spec.primitive_types:
        found = True

    if not found:
        n = context.get_global(name)
        if n is not None and n.name == '$type':
            found = True

    if not found and name != exclude:
        return False

    for t in typespec.subtypes:
        if not check_valid_type(t, items, context, exclude):
            return False

    return True

def convert_relative_typespec(t: TypeSpec, node: dict, items: ParsingItems, context: ParsingContext) -> TypeSpec:
    ts = TypeSpec(t.name, t.num_subtypes, [])

    if t.name.startswith('$'):
        val = node[t.name[1:]].value
        if isinstance(val, ValueToken):
            return val.var_type
        elif isinstance(val, OperatorInstance):
            return val.result_type
        ts.name = val

    for i in range(len(t.subtypes)):
        t.subtypes[i] = convert_relative_typespec(t.subtypes[i], node, items, context)

    return ts

def combine_dictionaries(dict1: dict, dict2: dict) -> dict:
    result = {}
    for k, v in dict1.items():
        result[k] = v
    for k,v in dict2.items():
        result[k] = v
    return result

def extract_scope_items(component: str, is_type: bool, parsed_variables: dict[str, SOInstanceItem]):
    if not component.startswith('$'):
        if is_type:
            return [string_to_typespec(component)]
        return [component]

    parts = component[1:].split('.')
    item = parsed_variables[parts[0]]

    stack = [item]

    for p_num in range(1, len(parts)):
        p = parts[p_num]
        sub_items = []
        for stack_item in stack:
            if stack_item.item_type == ComponentType.REPEATED_ELEMENT:
                for i in range(len(stack_item.value)):
                    if p not in stack_item.value[i]:
                        raise ValueError(f'item {p_num+1} ({p}) not found in {component}')
                    sub_item = stack_item.value[i][p]
                    sub_items.append(sub_item)
            else:
                if p not in stack_item.value:
                    raise ValueError(f'item {p_num+1} ({p}) not found in {component}')
                sub_item = stack_item.value[p]
                sub_items.append(sub_item)
        stack = sub_items

    variables = []

    if is_type:
        for item in stack:
            if not isinstance(item, TypenameInstance):
                raise ValueError(f'Component path {component} is of type {item.item_type}, not TypeName')
            variables.append(item.value)
    else:
        for item in stack:
            variables.append(item.value)

    return variables


class StructureParser:
    def __init__(self, items: ParsingItems, tokenizer_items: TokenizerItems):
        self.items = items
        self.tokenizer_items = tokenizer_items
        self.expression_parser = ExpressionParser(items)

    def __handle_typename(self, tokens: TokenIterator, context: ParsingContext, items: ParsingItems):
        # get typename, check primitive types
        tn, _ = next(tokens)
        # check primitive types - if primitive, return basic TypeSpec
        if tn.value in items.config_spec.primitive_types:
            return TypenameInstance(ComponentType.TYPENAME, TypeSpec(tn.value, 0, []))

        # check variables
        var_type = context.get_global(tn.value)
        if var_type is None:
            raise ValueError(f'Invalid type: {tn.value}')
        if var_type.name != '$type':
            raise ValueError(f'Invalid type: {tn.value}')
        return TypenameInstance(ComponentType.TYPENAME, var_type.subtypes[0])

    def __handle_name(self, comp: StructureComponent, structure: Structure, tokens: TokenIterator, context: ParsingContext):
        var = structure.component_specs[comp.value]

        var_type = 'existing-global'
        if 'type' in var.other:
            var_type = var.other['type']

        varname, _ = next(tokens)

        if var_type == 'existing-global':
            if not context.has_global(varname.value):
                raise RuntimeError(f'{varname} does not exist at line {varname.line}')
        elif var_type == 'existing-local':
            if not context.has_local(varname.value):
                raise RuntimeError(f'{varname} does not exist at line {varname.line}')
        elif var_type == 'new-global':
            if context.has_global(varname.value):
                raise RuntimeError(f'{varname} already exists at line {varname.line}')
        elif var_type == 'new-local':
            if context.has_local(varname.value):
                raise RuntimeError(f'{varname} already exists at line {varname.line}')
        elif var_type != 'any':
            raise RuntimeError(f'make-variable type "{var_type}" not recognized')

        return NameInstance(ComponentType.NAME, varname.value)

    def __handle_expression(self, tokens: TokenIterator, context: ParsingContext, items: ParsingItems, next_component: StructureComponent | None):
        until = ""
        if next_component is not None and next_component.component_type == StructureComponentType.String:
            until = next_component.value

        expression_parser = ExpressionParser(items)

        expression_parser.set_tokens_and_context(tokens, context)
        expr = expression_parser.parse(until)

        return SOInstanceItem(ComponentType.EXPRESSION, expr)

    def __handle_expressions(self, tokens: TokenIterator, context: ParsingContext, spec_component: StructureSpecComponent, parsed_variables, next_component: StructureComponent, items: ParsingItems, tokenizer_items: TokenizerItems):
        local = False
        if 'scope' in spec_component.other:
            if spec_component.other['scope'] == 'local':
                local = True
            elif spec_component.other['scope'] != 'global':
                raise RuntimeError(f"Unknown scope {spec_component.other['scope']} for expressions")

        returning_context: ParsingContext | None = None

        if local:
            block_context = ParsingContext(context)
            block_context.parent = context
            returning_context = block_context
        else:
            block_context = context

        filter = None
        if 'filter' in spec_component.other:
            filter = to_filter(spec_component.other['filter'])

        if 'insert_scope' in spec_component.other:
            if spec_component.other['insert_scope'] == 'global':
                raise ValueError("insert_scope can only be used with locally-scoped expressions")

            ins: list[dict] = spec_component.other['insert_scope']
            for comp in ins:
                ct: str = comp['type']
                cn: str = comp['name']

                var_types: list[TypeSpec] = extract_scope_items(ct, True, parsed_variables)
                var_names: list[str] = extract_scope_items(cn, False, parsed_variables)

                if len(var_names) != len(var_types):
                    if len(var_types) == 1:
                        var_types = [var_types[0]] * len(var_names)
                    else:
                        raise RuntimeError(f'Non-corresponding types and names for scope')

                for i in range(len(var_names)):
                    block_context.variables[var_names[i]] = var_types[i]

        sp = StructureParser(items, tokenizer_items)
        if not next_component:
            raise RuntimeError(f'Expressions variable in structure must have a following string')
        if next_component.component_type != StructureComponentType.String:
            raise NotImplementedError('Variable after an expressions structure component not implemented')
        result = sp.parse(tokens, block_context, until=next_component.value, filter=filter)
        if result is None:
            raise RuntimeError(f'Could not parse expressions')
        return SOInstanceItem(ComponentType.EXPRESSIONS, result, created_context=returning_context)

    def __handle_repeated_element(self, tokens: TokenIterator, context: ParsingContext, var_index: int, structure: Structure, items: ParsingItems, tokenizer_items: TokenizerItems):
        comp = structure.component_defs[var_index]
        var = structure.component_specs[comp.value]
        new_stucture = Structure(
            var.other['components'],
            comp.inner_structure
        )
        separator = comp.inner_fields['separator']

        repeat_end = structure.component_defs[var_index + 1]
        if repeat_end.component_type != StructureComponentType.String:
            raise RuntimeError(f'Variables after repeated structures are not yet supported.')

        sp = StructureParser(items, tokenizer_items)

        elements = []
        while tokens.peek().value != repeat_end.value:
            result = sp.__parse_single_structure(tokens, new_stucture, context)
            if tokens.peek().value != separator and tokens.peek().value != repeat_end.value:
                raise RuntimeError(f"Unable to parse component structure at {tokens.peek()}")
            if tokens.peek().value == separator:
                next(tokens)
            elements.append(result)

        return SOInstanceItem(ComponentType.REPEATED_ELEMENT, elements)

    def __handle_structure(self, tokens: TokenIterator, context: ParsingContext, var_index: int, structure, parsed_variables: dict[str, SOInstanceItem], items: ParsingItems):
        comp = structure.component_defs[var_index]
        var = structure.component_specs[comp.value]
        next_structure_name = var.other['structure']

        next_structure = items.config_spec.structured_objects[next_structure_name]
        originals = {}
        next_comp_specs = next_structure.structure.component_specs
        if 'modifiers' in var.other and var.name in var.other['modifiers']:
            mods = var.other['modifiers'][var.name]

            for item, val in mods.items():
                if item in next_comp_specs[var.name].other:
                    originals[item] = next_comp_specs[var.name].other[item]
                else:
                    originals[item] = None
                next_comp_specs[var.name].other[item] = val

        node = self.__parse_single_structure(tokens, next_structure.structure, context, parsed_variables)
        sobj = StructuredObjectInstance(next_structure, node)

        for o, val in originals.items():
            if val is None:
                del next_comp_specs[var.name].other[o]
            else:
                next_comp_specs[var.name].other[o] = val

        return SOInstanceItem(ComponentType.STRUCTURE, sobj)

    def __handle_variable(self, var_index: int, structure: Structure, tokens: TokenIterator,
                          context: ParsingContext, parsed_variables: dict[str, SOInstanceItem]):
        comp = structure.component_defs[var_index]
        next_comp = structure.component_defs[var_index+1] if var_index < len(structure.component_defs) - 1 else None
        if comp.value not in structure.component_specs:
            raise RuntimeError(f"structure component {comp.value} not found")
        var = structure.component_specs[comp.value]

        result = None

        if var.base == ComponentType.TYPENAME:
            result = self.__handle_typename(tokens, context, self.items)
        elif var.base == ComponentType.NAME:
            result = self.__handle_name(comp, structure, tokens, context)
        elif var.base == ComponentType.EXPRESSION:
            result = self.__handle_expression(tokens, context, self.items, next_comp)
        elif var.base == ComponentType.EXPRESSIONS:
            spec_comp = structure.component_specs[comp.value]
            result = self.__handle_expressions(tokens, context, spec_comp, parsed_variables, next_comp, self.items, self.tokenizer_items)
        elif var.base == ComponentType.REPEATED_ELEMENT:
            result = self.__handle_repeated_element(tokens, context, var_index, structure)

        elif var.base == ComponentType.STRUCTURE:
            result = self.__handle_structure(tokens, context, var_index, structure, parsed_variables)

        else:
            raise RuntimeError(f'base {var.base} not recognized')

        return var.name, result

    def __parse_single_structure(self, tokens: TokenIterator, structure: Structure, context: ParsingContext, parsed_variables: dict[str, SOInstanceItem] | None = None):
        structure_count = 0
        reference_parsed_variables = parsed_variables or {}
        parsed_variables: dict[str, SOInstanceItem] = {}

        while structure_count < len(structure.component_defs) and not tokens.done():
            s = structure.component_defs[structure_count]

            if s.component_type == StructureComponentType.Variable:
                combined_vars = combine_dictionaries(reference_parsed_variables, parsed_variables)
                n, v = self.__handle_variable(structure_count, structure, tokens, context, combined_vars)
                parsed_variables[n] = v
                structure_count += 1

            elif s.component_type == StructureComponentType.String:
                string_tokens = Tokenizer(self.tokenizer_items).tokenize(s.value)
                for token in string_tokens:
                    tn, _ = next(tokens)
                    if tn.value != token.value:
                        raise RuntimeError(f'Expected {token.value}, got {tn.value} at line {tn.line}')
                structure_count += 1

            elif s.component_type == StructureComponentType.Command:
                pass

            elif s.component_type == StructureComponentType.EndCommand:
                pass

        return parsed_variables

    def __create_structure_list(self, tokens: TokenIterator, context: ParsingContext, filter: StructureFilter | None = None) -> list[StructuredObjectInstance]:
        token = tokens.peek()

        possible_structures: list[StructuredObjectInstance] = []

        is_filtering = filter and not filter.all

        for so in self.items.config_spec.structured_objects.values():
            if is_filtering and not filter.matches(so):
                continue
            if len(so.structure.component_defs) == 0 or (not is_filtering and so.dependent):
                continue
            first_component = so.structure.component_defs[0]
            if first_component.component_type == StructureComponentType.String and first_component.value == token.value:
                soi = StructuredObjectInstance(so, {})
                possible_structures.append(soi)

            elif first_component.component_type == StructureComponentType.Variable:
                spec_component = so.structure.component_specs[first_component.value]

                if spec_component.base == ComponentType.EXPRESSION:
                    exp = ExpressionParser(self.items)
                    test_iterator = TokenIterator(tokens.tokens[tokens.index:])
                    exp.set_tokens_and_context(test_iterator, context)
                    result = exp.parse_until_full_tree()
                    if result is not None:
                        component_dict = {spec_component.name: result}
                        soi = StructuredObjectInstance(so, component_dict)
                        possible_structures.append(soi)

                elif spec_component.base == ComponentType.TYPENAME:
                    if token.value in self.items.config_spec.primitive_types:
                        component_dict = {spec_component.name: token}
                        soi = StructuredObjectInstance(so, component_dict)
                        possible_structures.append(soi)
                    else:
                        v = context.get_global(token.value)
                        if v is not None and v.name == "$type":
                            component_dict = {spec_component.name: token}
                            soi = StructuredObjectInstance(so, component_dict)
                            possible_structures.append(soi)


                elif spec_component.base == ComponentType.NAME:
                    if context.has_global(token.value):
                        component_dict = {spec_component.name: context.get_global(token.value)}
                        soi = StructuredObjectInstance(so, component_dict)
                        possible_structures.append(soi)

                else:
                    raise ValueError(f"Unknown base {spec_component.base} for component {spec_component.name}")

        return possible_structures

    def parse(self, tokens: TokenIterator, context: ParsingContext, until="", filter: StructureFilter | None = None) -> list[StructuredObjectInstance | OperatorInstance | ValueToken]:

        ast_nodes = []
        while not tokens.done():
            if until != "" and tokens.peek().value == until:
                break

            possible_structures = self.__create_structure_list(tokens, context, filter)

            if len(possible_structures) == 0:
                if filter and not filter.allow_expressions:
                    raise RuntimeError(f"Invalid syntax on line {tokens.peek().line}")
                exp = ExpressionParser(self.items)
                exp.set_tokens_and_context(tokens, context)
                result = exp.parse()
                ast_nodes.append(result)
                continue

            working_structures = []
            token_nums = []

            cur_index = tokens.index

            errors_found = []

            for structure in possible_structures:
                try:
                    node = self.__parse_single_structure(tokens, structure.so.structure, context)
                    structure.components = node
                    working_structures.append((structure, node))
                    token_nums.append(tokens.index)
                except RuntimeError as e:
                    errors_found.append(f"{structure.so.name}: {e}")
                    pass

                tokens.goto(cur_index)

            if len(working_structures) == 0:
                if len(errors_found) == 1:
                    raise RuntimeError(errors_found[0])

                total_error = "Possible Structure Errors:"
                for e in errors_found:
                    total_error += f"\n\t{e}"
                raise RuntimeError(total_error)

            max_components = 0
            max_structure: None | tuple[StructuredObjectInstance, dict[str, SOInstanceItem]] = None
            max_index = 0
            for i in range(len(working_structures)):
                if len(working_structures[i][1]) > max_components:
                    max_components = len(working_structures[i][1])
                    max_structure = working_structures[i]
                    max_index = token_nums[i]

            max_soi = max_structure[0]
            max_soi_vars: dict[str, SOInstanceItem] = max_structure[1]

            ast_nodes.append(max_soi)
            tokens.goto(max_index)

            # CREATES VARIABLE
            if max_soi.so.create_variable:
                cv = max_soi.so.create_variable
                name = cv.name
                if name.startswith('$'):
                    name = max_soi_vars[name[1:]].value
                so_type = cv.type
                if so_type.name.startswith('$'):
                    so_type = max_soi_vars[so_type.name[1:]].value

                if cv.check_type:
                    st = string_to_typespec(cv.check_type)
                    t = convert_relative_typespec(
                        st,
                        max_soi_vars,
                        self.items,
                        context
                    )
                    if not typespec_matches(t, so_type):
                        if tokens.peek() is None:
                            tokens.goto(tokens.current_index() - 1)
                        raise RuntimeError(f"Type mismatch: {t} != {so_type.name} on line {tokens.peek().line}")


                context.variables[name] = so_type

            # CREATES TYPE
            if max_soi.so.create_type:
                # create typespec of type $type
                type_type = convert_relative_typespec(
                    max_soi.so.create_type.type,
                    max_soi_vars,
                    self.items,
                    context
                )
                if not check_valid_type(type_type, self.items, context, exclude=type_type.name):
                    raise RuntimeError(f"Invalid type {type_type} for {max_soi.so.name}")
                full_typespec = TypeSpec("$type", 1, [type_type])

                # get attributes
                for container in max_soi.so.create_type.fields_containers:
                    parts = container.replace(' ', '').split('.')
                    item = max_soi_vars[parts[0]]
                    for part in parts[1:]:
                        item = item.value.components[part]
                    cont_context = item.created_context
                    if cont_context is None:
                        raise RuntimeError(f"Field container {container} does not have a context defined. Change this item to have local scope.")
                    for var_name, var_type in cont_context.variables.items():
                        full_typespec.attributes[var_name] = var_type

                context.variables[type_type.name] = full_typespec

                context.variables[type_type.name] = full_typespec

        return ast_nodes
