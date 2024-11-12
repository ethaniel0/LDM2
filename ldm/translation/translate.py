from dataclasses import dataclass
from ldm.lib_config2.parsing_types import ExpressionSeparator, StructureComponentType as SCT
from ldm.ast.parsing_types import (ParsingItems,
                                   MakeVariableInstance,
                                   OperatorInstance,
                                   ValueToken,
                                   TypeSpec)
from ldm.translation.translation_types import (MakeVariableTranslation,
                                               StructureComponentType,
                                               OperatorTranslation,
                                               StructureComponent,
                                               PrimitiveTypeTranslation,
                                               ValueKeywordTranslation,
                                               parse_translate_into_components)



@dataclass
class TranslationItems:
    make_variables: dict[str, MakeVariableTranslation]
    primitive_types: dict[str, PrimitiveTypeTranslation]
    operators: dict[str, OperatorTranslation]
    value_keywords: dict[str, ValueKeywordTranslation]
    expression_separators: dict[str, ExpressionSeparator]

    def __init__(self, specs: dict):
        self.make_variables = {}
        self.primitive_types = {}
        self.value_keywords = {}
        self.expression_separators = {}
        self.operators = {}

        for item in specs:
            if 'type' not in item:
                raise RuntimeError('Translation item missing "type" field')
            if 'name' not in item:
                raise RuntimeError('Translation item missing "name" field')

            if item['type'] == 'make_variable':
                components = parse_translate_into_components(item['translate'])
                self.make_variables[item['name']] = MakeVariableTranslation(item['type'],
                                                                            item['name'],
                                                                            components)
            elif item['type'] == 'primitive_type':
                self.primitive_types[item['name']] = PrimitiveTypeTranslation(item['type'],
                                                                              item['name'],
                                                                              item['translate'])
            elif item['type'] == 'value_keyword':
                self.value_keywords[item['name']] = ValueKeywordTranslation(item['type'],
                                                                            item['name'],
                                                                            item['translate'])
            elif item['type'] == 'expression_separator':
                self.expression_separators[item['name']] = ExpressionSeparator(item['name'], item['translate'])

            elif item['type'] == 'operator':
                components = parse_translate_into_components(item['translate'])
                self.operators[item['name']] = OperatorTranslation(item['type'],
                                                                   item['name'],
                                                                   components)
        
        if len(self.expression_separators) == 0:
            self.expression_separators['main'] = ExpressionSeparator('main', '')


def translate_type(name: str, translation_items: TranslationItems):
    if name not in translation_items.primitive_types:
        raise RuntimeError(f'Primitive type "{name}" not found in translation items')
    return translation_items.primitive_types[name].translate


def matches_type(expression_type: TypeSpec, necessary_type, parsing_items: ParsingItems):
    if expression_type.name == necessary_type:
        return True
    # check for downstream "is" relationship
    types = parsing_items.config_spec.primitive_types
    if expression_type.name not in types:
        raise RuntimeError(f'Primitive type "{expression_type}" not found in spec')
    if necessary_type not in types:
        raise RuntimeError(f'Primitive type "{necessary_type}" not found in spec')

    val = types[necessary_type]
    while val.superclass:
        if val.superclass == expression_type:
            return True
        val = types[val.superclass.name]

    return False


def translate_value_token(value_token: ValueToken, translation: TranslationItems) -> str:
    if value_token.value.value in translation.value_keywords:
        return translation.value_keywords[value_token.value.value].translate
    return value_token.value.value


def translate_operator_instance(operator_instance: OperatorInstance, translation: TranslationItems) -> str:
    defs = operator_instance.operator.structure.component_defs
    named_values_list: list[StructureComponent] = list(filter(lambda d: d.component_type == SCT.Variable, defs))

    named_values = {named_values_list[i].value: operator_instance.operands[i] for i in range(len(named_values_list))}

    code = ""

    for component in translation.operators[operator_instance.operator.name].translate:
        comp_name = component.value

        if component.component_type == StructureComponentType.String or \
                component.component_type == StructureComponentType.Whitespace:
            code += comp_name
            continue

        if comp_name not in named_values:
            raise RuntimeError(f'Operator "{operator_instance.operator.name}" missing value for "{comp_name}"')

        value = named_values[comp_name]

        if isinstance(value, ValueToken):
            code += translate_value_token(value, translation)
        elif isinstance(value, OperatorInstance):
            code += translate_operator_instance(value, translation)

    return code


def translate_make_variable(mv: MakeVariableInstance,
                            parsing_items: ParsingItems,
                            translation: TranslationItems,
                            indentation=0) -> str:
    if mv.name not in translation.make_variables:
        raise RuntimeError(f'Make Variable "{mv.name}" not found in translation items')
    mv_translation = translation.make_variables[mv.name]

    mv_ref = parsing_items.config_spec.make_variables[mv.name]

    code = "\t"*indentation

    for component in mv_translation.translate:
        if (component.component_type == StructureComponentType.String or
                component.component_type == StructureComponentType.Whitespace):
            code += component.value
            if component.value == '\n':
                code += "\t"*indentation

        elif component.component_type == StructureComponentType.Variable:
            var_name = component.value
            if var_name not in mv.structure:
                raise RuntimeError(f'Variable "{var_name}" not found in Make Variable "{mv.name}"')

            spec = mv_ref.structure.component_specs[var_name]

            if spec.base == 'typename':
                code += translate_type(mv.structure[var_name].value, translation)
            elif spec.base == 'name':
                code += mv.structure[var_name].value
            elif spec.base == 'expression':
                # TODO: implement expression translation
                t: OperatorInstance | ValueToken = mv.structure[var_name]
                if isinstance(t, ValueToken):
                    code += translate_value_token(t, translation)
                elif isinstance(t, OperatorInstance):
                    code += translate_operator_instance(t, translation)
            else:
                raise RuntimeError(f'Unknown structure component base "{spec.base}"')

    return code


def translate(ast: list, parsing_items: ParsingItems, translation: TranslationItems) -> str:
    code = ""
    for item in ast:
        if isinstance(item, MakeVariableInstance):
            code += translate_make_variable(item, parsing_items, translation)
            code += translation.expression_separators['main'].value
        else:
            raise RuntimeError(f'Unexpected AST item: {item}')
    return code
