from __future__ import annotations

from ldm.ast.type_checking import typespec_matches, type_operator
from ldm.lib_config2.spec_parsing import string_to_typespec
from ldm.source_tokenizer.tokenize import Token, TokenizerItems, Tokenizer
from ldm.ast.parsing_types import (TokenIterator, ParsingItems, ParsingContext,
                                   OperatorInstance, ValueToken,
                                   StructuredObjectInstance, NameInstance, TypenameInstance, SOInstanceItem)
from ldm.lib_config2.parsing_types import Structure, StructureComponentType, StructureComponent, TypeSpec, \
    ComponentType, StructureFilter, StructureFilterComponent, StructureFilterComponentType, StructuredObject, \
    Associativity, OperatorType
from ldm.source_tokenizer.tokenizer_types import TokenType


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
        val = node[t.name[1:]]
        if isinstance(val, ValueToken):
            return val.var_type
        elif isinstance(val, StructuredObjectInstance):
            return val.operator_fields.result_type
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
                    if p not in stack_item.value[i].components:
                        raise ValueError(f'item {p_num+1} ({p}) not found in {component}')
                    sub_item = stack_item.value[i].components[p]
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

    def __handle_typename(self, tokens: TokenIterator, context: ParsingContext):
        # get typename, check primitive types
        tn, _ = next(tokens)
        # check primitive types - if primitive, return basic TypeSpec
        if tn.value in self.items.config_spec.primitive_types:
            return TypenameInstance(ComponentType.TYPENAME, TypeSpec(tn.value, 0, []), tn)

        # check variables
        var_type = context.get_global(tn.value)
        if var_type is None:
            raise ValueError(f'Invalid type: {tn.value}')
        if var_type.name != '$type':
            raise ValueError(f'Invalid type: {tn.value}')
        return TypenameInstance(ComponentType.TYPENAME, var_type.subtypes[0], tn)

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

        return NameInstance(ComponentType.NAME, varname.value, varname)

    def __handle_expression(
            self,
            tokens: TokenIterator,
            context: ParsingContext,
            var_index: int,
            structure: Structure,
            filter: StructureFilter | None,
            short: bool = False
    ):
        until = ""
        if var_index < len(structure.component_defs) - 1:
            next_comp = structure.component_defs[var_index + 1]
            if next_comp.component_type == StructureComponentType.String:
                until = next_comp.value

        if short:
            expr = self.__parse_expression_to_full_tree(tokens, context, [], None, filter)
        else:
            expr = self.__parse_expression(tokens, context, filter, until)
        next_token = tokens.peek()
        return SOInstanceItem(ComponentType.EXPRESSION, expr, next_token)

    def __handle_expressions(self, tokens: TokenIterator, context: ParsingContext, var_index: int, structure: Structure, parsed_variables):
        comp = structure.component_defs[var_index]
        var = structure.component_specs[comp.value]

        local = False
        if 'scope' in var.other:
            if var.other['scope'] == 'local':
                local = True
            elif var.other['scope'] != 'global':
                raise RuntimeError(f"Unknown scope {var.other['scope']} for expressions")

        returning_context: ParsingContext | None = None

        if local:
            block_context = ParsingContext(context)
            block_context.parent = context
            returning_context = block_context
        else:
            block_context = context

        filter = None
        if 'filter' in var.other:
            filter = to_filter(var.other['filter'])

        if 'insert_scope' in var.other:
            if var.other['insert_scope'] == 'global':
                raise ValueError("insert_scope can only be used with locally-scoped expressions")

            ins: list[dict] = var.other['insert_scope']
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

        sp = StructureParser(self.items, self.tokenizer_items)
        if len(structure.component_defs) <= var_index + 1:
            raise RuntimeError(f'Expressions variable in structure must have a following string')
        next_comp_def = structure.component_defs[var_index + 1]
        if next_comp_def.component_type != StructureComponentType.String:
            raise NotImplementedError('Variable after an expressions structure component not implemented')

        next_token = tokens.peek()
        result = sp.parse(tokens, block_context, until=next_comp_def.value, filter=filter)
        if result is None:
            raise RuntimeError(f'Could not parse expressions')
        return SOInstanceItem(ComponentType.EXPRESSIONS, result, next_token, created_context=returning_context)

    def __handle_repeated_element(self, tokens: TokenIterator, context: ParsingContext, var_index: int, structure: Structure, filter: StructureFilter | None):
        comp = structure.component_defs[var_index]
        var = structure.component_specs[comp.value]
        new_structure = Structure(
            var.other['components'],
            comp.inner_structure
        )

        separator = comp.inner_fields['separator']

        repeat_end = structure.component_defs[var_index + 1]
        if repeat_end.component_type != StructureComponentType.String:
            raise RuntimeError(f'Variables after repeated structures are not yet supported.')

        sp = StructureParser(self.items, self.tokenizer_items)

        first_token = tokens.peek()

        elements = []
        while tokens.peek().value != repeat_end.value:
            try:
                new_soi = StructuredObjectInstance(StructuredObject("", new_structure), {})
                sp.__parse_single_structure(tokens, new_soi, context, filter=filter)
                if tokens.peek().value != separator and tokens.peek().value != repeat_end.value:
                    raise RuntimeError(f"Unable to parse component structure at {tokens.peek()}")
                if tokens.peek().value == separator:
                    next(tokens)
                elements.append(new_soi)
            except RuntimeError:
                break

        return SOInstanceItem(ComponentType.REPEATED_ELEMENT, elements, first_token)

    def __handle_structure(self, tokens: TokenIterator, context: ParsingContext, var_index: int, structure, parsed_variables: dict[str, SOInstanceItem], filter: StructureFilter | None):
        comp = structure.component_defs[var_index]
        var = structure.component_specs[comp.value]
        next_structure_name = var.other['structure']

        next_structure = self.items.config_spec.structured_objects[next_structure_name]

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

        next_soi = StructuredObjectInstance(next_structure, {})

        next_token = tokens.peek()

        self.__parse_single_structure(tokens, next_soi, context, parsed_variables, filter=filter)

        for o, val in originals.items():
            if val is None:
                del next_comp_specs[var.name].other[o]
            else:
                next_comp_specs[var.name].other[o] = val

        return SOInstanceItem(ComponentType.STRUCTURE, next_soi, next_token)

    def __handle_variable(
            self,
            var_index: int,
            structure: Structure,
            tokens: TokenIterator,
            context: ParsingContext,
            parsed_variables: dict[str, SOInstanceItem],
            filter: StructureFilter | None,
            last_expression_short: bool = False
    ):
        comp = structure.component_defs[var_index]
        if comp.value not in structure.component_specs:
            raise RuntimeError(f"structure component {comp.value} not found")
        var = structure.component_specs[comp.value]

        if var.base == ComponentType.TYPENAME:
            result = self.__handle_typename(tokens, context)
        elif var.base == ComponentType.NAME:
            result = self.__handle_name(comp, structure, tokens, context)
        elif var.base == ComponentType.EXPRESSION:
            result = self.__handle_expression(tokens, context, var_index, structure, filter, last_expression_short)
            result = result.value
        elif var.base == ComponentType.EXPRESSIONS:
            result = self.__handle_expressions(tokens, context, var_index, structure, parsed_variables)
        elif var.base == ComponentType.REPEATED_ELEMENT:
            result = self.__handle_repeated_element(tokens, context, var_index, structure, filter)
        elif var.base == ComponentType.STRUCTURE:
            result = self.__handle_structure(tokens, context, var_index, structure, parsed_variables, filter)

        else:
            raise RuntimeError(f'base {var.base} not recognized')

        return var.name, result

    def __parse_value(self, token: Token, context: ParsingContext) -> ValueToken:
        init_formats = self.items.config_spec.initializer_formats

        if token.type == TokenType.Integer:
            if '$int' in init_formats:
                ts = TypeSpec(init_formats['$int'].ref_type, 0, [])
                return ValueToken(token, ts, None)
            raise RuntimeError(f'No initializer format for int')

        if token.type == TokenType.Float:
            if '$float' in init_formats:
                ts = TypeSpec(init_formats['$float'].ref_type, 0, [])
                return ValueToken(token, ts, None)
            raise RuntimeError(f'No initializer format for float')

        if token.type == TokenType.String:
            if '$string' in init_formats:
                ts = TypeSpec(init_formats['$string'].ref_type, 0, [])
                return ValueToken(token, ts, None)
            raise RuntimeError(f'No initializer format for string')

        if token.type == TokenType.ValueKeyword:
            if token.value in init_formats:
                ts = TypeSpec(init_formats[token.value].ref_type, 0, [])
                return ValueToken(token, ts, None)
            raise RuntimeError(f'No initializer format for {token.value}')

        if token.type == TokenType.Identifier:
            v = context.get_global(token.value)
            if v is None:
                raise RuntimeError(f'{token} not defined at line {token.line}')
            return ValueToken(token, v, None)

        raise RuntimeError(f'Could not parse value "{token.value}" at line {token.line}')


    def __order_operator_in_tree(self, stack, tree: ValueToken | StructuredObjectInstance | None, item: ValueToken | StructuredObjectInstance):

        if isinstance(item, ValueToken):
            if tree is None:
                return item
            raise RuntimeError(f"\"{item.value}\" cannot be used as an operator")

        has_left = item.operator_fields.op_type in [OperatorType.UNARY_LEFT, OperatorType.BINARY]
        num_lefts = item.operator_num_lefts()

        if tree is None and has_left:
            if len(stack) < num_lefts:
                raise RuntimeError(f"Operator {item.so.name} does not have a left operand")

            for i in range(num_lefts):
                name = item.so.structure.component_defs[i].value
                item.components[name] = stack[len(stack) - num_lefts + i]

            for i in range(num_lefts):
                stack.pop()

            return item

        if has_left:

            if num_lefts > 1:
                stack.append(tree)
                for i in range(num_lefts - 1):
                    name = item.so.structure.component_defs[i].value
                    item.components[name] = stack[len(stack) - num_lefts - 1 + i]

                for i in range(num_lefts - 1):
                    stack.pop()

                tree = stack[-1]

            if isinstance(tree, ValueToken):
                first_expr = item.so.structure.component_defs[0].value
                item.components[first_expr] = tree
            else:
                while item.so.create_operator.precedence > tree.so.create_operator.precedence or \
                        (item.so.create_operator.precedence == tree.so.create_operator.precedence and
                         item.so.create_operator.associativity == Associativity.LEFT_TO_RIGHT) or \
                        tree.operator_fields.op_type in [OperatorType.UNARY_LEFT, OperatorType.INTERNAL]:
                    if tree.operator_fields_filled() != len(tree.so.create_operator.fields):
                        raise RuntimeError(f'Operator {tree.so.name} not fully parsed')
                    if tree.operator_fields.parse_parent is None:
                        first_expr = item.so.structure.component_defs[0].value
                        item.components[first_expr] = tree
                        tree = item
                        break
                    tree = tree.operator_fields.parse_parent

                if item != tree:
                    tree_last_expr = item.so.structure.component_defs[-1].value
                    item_first_expr = item.so.structure.component_defs[0].value
                    item.components[item_first_expr] = tree.components[tree_last_expr]
                    tree.components[tree_last_expr] = item
                    item.operator_fields.parse_parent = tree

                return tree

        else:
            if len(item.components) == 0:
                raise RuntimeError(f"Unexpected Operator {item.so.name} (line coming later)")
            first_filled_var = list(item.components.values())[0]
            raise RuntimeError(f'Unexpected operator {item.so.name} at line {first_filled_var.token.line}')

    def __parse_expression_to_full_tree(self,
                                        tokens: TokenIterator,
                                        context: ParsingContext,
                                        stack: list[ValueToken | StructuredObjectInstance],
                                        tree: ValueToken | StructuredObjectInstance | None,
                                        active_filter: StructureFilter):
        while not tokens.done():
            if tokens.peek().type == TokenType.ExpressionSeparator:
                next(tokens)
                break

            structures = self.__create_structure_list(tokens, context, active_filter, skip_first_expressions=True)

            parse_as_variable = False
            max_structure, max_structure_index = None, 0

            # parse as variable or literal
            if len(structures) == 0:
                parse_as_variable = True
            # parse structures
            else:
                result = self.__test_structures(
                    tokens,
                    structures,
                    context,
                    active_filter,
                    error_on_failure=False,
                    skip_first_expressions=True,
                    last_expression_short=True
                )
                if result is None:
                    parse_as_variable = True
                else:
                    max_structure, max_structure_index = result

            if parse_as_variable:
                t, _ = next(tokens)
                val = self.__parse_value(t, context)
                stack.append(val)

            else:
                try:
                    tree = self.__order_operator_in_tree(stack, tree, max_structure)
                    tokens.goto(max_structure_index)
                except RuntimeError as _:
                    stack.append(tree)

            if len(stack) == 1 and tree is None:
                return stack[0]

            if tree and tree.operator_fields_filled() == len(tree.so.create_operator.fields):
                head = tree
                while tree.operator_fields.parse_parent is not None:
                    head = tree.operator_fields.parse_parent
                return head

        if tree and len(stack) != 0 or not tree and len(stack) != 1:
            return None
        if tree and tree.operator_fields_filled() < len(tree.so.create_operator.fields):
            return None

        if tree:
            return tree

        return stack[0]

    def __parse_expression(self,
                           tokens: TokenIterator,
                           context: ParsingContext,
                           filter: StructureFilter | None,
                           until=""):
        if not filter:
            filter = StructureFilter()
        else:
            filter = filter.clone()

        filter.add_filter(
            StructureFilterComponent(StructureFilterComponentType.CONTAINS, "create_operator")
        )

        stack = []

        tree: None | ValueToken | StructuredObjectInstance = None

        while not tokens.done():
            if tokens.peek().type == TokenType.ExpressionSeparator:
                next(tokens)
                break
            if until and tokens.peek().value == until:
                break

            result = self.__parse_expression_to_full_tree(tokens, context, stack, tree, filter)
            if isinstance(result, StructuredObjectInstance):
                tree = result

        if isinstance(tree, StructuredObjectInstance):
            stack.append(tree)

        if len(stack) > 1:
            raise RuntimeError(f'Expression does not simplify to a singular value at line {stack[0].value.line}')

        if isinstance(stack[0], StructuredObjectInstance):
            type_operator(stack[0], self.items)
        return stack[0]

    def __parse_single_structure(
            self,
            tokens: TokenIterator,
            soi: StructuredObjectInstance,
            context: ParsingContext,
            referenced_parsed_variables: dict[str, SOInstanceItem] | None = None,
            from_index: int = 0,
            filter: StructureFilter | None = None,
            last_expression_short: bool = False,
    ):
        structure_count = from_index
        reference_parsed_variables = referenced_parsed_variables or {}
        structure = soi.so.structure

        while structure_count < len(structure.component_defs) and not tokens.done():
            s = structure.component_defs[structure_count]
            is_last = structure_count == len(structure.component_defs) - 1

            if s.component_type == StructureComponentType.Variable:
                combined_vars = combine_dictionaries(reference_parsed_variables, soi.components)
                n, v = self.__handle_variable(structure_count, structure, tokens, context, combined_vars, filter, last_expression_short and is_last)
                soi.components[n] = v
                structure_count += 1

            elif s.component_type == StructureComponentType.String:
                string_tokens = Tokenizer(self.tokenizer_items).tokenize(s.value)
                for token in string_tokens:
                    tn, _ = next(tokens)
                    if tn.value != token.value:
                        raise RuntimeError(f'Expected {token.value}, got {tn.value} at line {tn.line}')
                structure_count += 1

    def __create_structure_list(self, tokens: TokenIterator, context: ParsingContext, filter: StructureFilter | None = None, skip_first_expressions: bool = False) -> list[StructuredObjectInstance]:
        token = tokens.peek()
        cur_index = tokens.current_index()

        possible_structures: list[StructuredObjectInstance] = []

        is_filtering = filter and not filter.all

        for so in self.items.config_spec.structured_objects.values():
            if is_filtering and not filter.matches(so):
                continue
            if len(so.structure.component_defs) == 0 or (not is_filtering and so.dependent):
                continue
            first_component = so.structure.component_defs[0]

            if skip_first_expressions:
                for ind, d in enumerate(so.structure.component_defs):
                    if d.component_type != StructureComponentType.Variable or \
                            so.structure.component_specs[d.value].base != ComponentType.EXPRESSION:
                        first_component = d
                        break


            if first_component.component_type == StructureComponentType.String and first_component.value == token.value:
                soi = StructuredObjectInstance(so, {})
                possible_structures.append(soi)

            elif first_component.component_type == StructureComponentType.Variable:
                spec_component = so.structure.component_specs[first_component.value]

                if spec_component.base == ComponentType.EXPRESSION:
                    try:
                        result = self.__parse_expression(tokens, context, filter)
                        if result is not None:
                            component_dict = {spec_component.name: result}
                            soi = StructuredObjectInstance(so, component_dict)
                            possible_structures.append(soi)
                        tokens.goto(cur_index)
                    except:
                        tokens.goto(cur_index)
                        continue

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

    def __test_structures(
            self, tokens: TokenIterator,
            structures: list[StructuredObjectInstance],
            context: ParsingContext,
            active_filter: StructureFilter | None,
            error_on_failure: bool = True,
            skip_first_expressions: bool = False,
            last_expression_short: bool = False,
    ):
        if len(structures) == 0:
            if active_filter and not active_filter.allow_expressions:
                if error_on_failure:
                    raise RuntimeError(f"Invalid syntax on line {tokens.peek().line}")
                return None
            result = self.__parse_expression(tokens, context, active_filter)
            return result

        working_structures = []
        token_nums = []

        cur_index = tokens.index

        errors_found = []

        for structure in structures:
            start_index = 0
            if skip_first_expressions:
                for d in structure.so.structure.component_defs:
                    if d.component_type != StructureComponentType.Variable:
                        break
                    if structure.so.structure.component_specs[d.value].base == ComponentType.EXPRESSION:
                        start_index += 1
                    else:
                        break

            try:
                self.__parse_single_structure(tokens, structure, context, from_index=start_index, filter=active_filter, last_expression_short=last_expression_short)
                working_structures.append(structure)
                token_nums.append(tokens.index)
            except RuntimeError as e:
                errors_found.append(f"{structure.so.name}: {e}")
                pass

            tokens.goto(cur_index)

        if len(working_structures) == 0:
            if error_on_failure:
                if len(errors_found) == 1:
                    raise RuntimeError(errors_found[0])

                total_error = "Possible Structure Errors:"
                for e in errors_found:
                    total_error += f"\n\t{e}"
                raise RuntimeError(total_error)

            return None

        max_components = 0
        max_structure: None | StructuredObjectInstance = None
        max_index = 0
        for i in range(len(working_structures)):
            if len(working_structures[i].components) > max_components:
                max_components = len(working_structures[i].components)
                max_structure = working_structures[i]
                max_index = token_nums[i]

        return max_structure, max_index

    def parse(self, tokens: TokenIterator, context: ParsingContext, until="", filter: StructureFilter | None = None) -> list[StructuredObjectInstance | OperatorInstance | ValueToken]:

        ast_nodes = []
        while not tokens.done():
            if until != "" and tokens.peek().value == until:
                break

            possible_structures = self.__create_structure_list(tokens, context, filter)

            best_structure, best_index = self.__test_structures(tokens, possible_structures, context, filter, True)

            max_soi = best_structure
            max_soi_vars: dict[str, SOInstanceItem] = best_structure.components

            ast_nodes.append(max_soi)
            tokens.goto(best_index)

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
