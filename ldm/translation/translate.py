from dataclasses import dataclass
from ldm.lib_config2.parsing_types import ExpressionSeparator, StructureComponentType as SCT
from ldm.ast.parsing_types import (ParsingItems,
                                   OperatorInstance,
                                   ValueToken,
                                   TypeSpec,
                                   StructuredObjectInstance,
                                   BlockInstance, TypenameInstance, NameInstance)
from ldm.translation.translation_types import (StructuredObjectTranslation,
                                               StructureComponentType,
                                               OperatorTranslation,
                                               StructureComponent,
                                               PrimitiveTypeTranslation,
                                               ValueKeywordTranslation,
                                               parse_translate_into_components,
                                               BlockTranslation)


@dataclass
class TranslationItems:
    structured_objects: dict[str, StructuredObjectTranslation]
    primitive_types: dict[str, PrimitiveTypeTranslation]
    operators: dict[str, OperatorTranslation]
    value_keywords: dict[str, ValueKeywordTranslation]
    expression_separators: dict[str, ExpressionSeparator]
    blocks: dict[str, BlockTranslation]

    def __init__(self, specs: dict):
        self.structured_objects: dict[str, StructuredObjectTranslation] = {}
        self.primitive_types: dict[str, PrimitiveTypeTranslation] = {}
        self.operators: dict[str, OperatorTranslation] = {}
        self.value_keywords: dict[str, ValueKeywordTranslation] = {}
        self.expression_separators: dict[str, ExpressionSeparator] = {}
        self.blocks: dict[str, BlockTranslation] = {}

        for item in specs:
            if 'type' not in item:
                raise RuntimeError('Translation item missing "type" field')
            if 'name' not in item:
                raise RuntimeError('Translation item missing "name" field')

            if item['type'] in ['make_variable', 'make_object', 'keyword']:
                components = parse_translate_into_components(item['translate'])
                self.structured_objects[item['name']] = StructuredObjectTranslation(item['type'],
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
            elif item['type'] == 'block':
                components = parse_translate_into_components(item['translate'])
                self.blocks[item['name']] = BlockTranslation(item['type'],
                                                             item['name'],
                                                             components,
                                                             item['indent'])
        
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


def translate_block(block: BlockInstance, parsing_items: ParsingItems, translation: TranslationItems, indentation) -> str:
    if block.block.name not in translation.blocks:
        raise RuntimeError(f'Block "{block.block.name}" not found in translation items')
    block_translation = translation.blocks[block.block.name]

    code = ""

    for component in block_translation.translate:
        if component.component_type == StructureComponentType.String:
            code += component.value
        elif component.component_type == StructureComponentType.Variable:
            if component.value not in block.components:
                raise RuntimeError(f'Variable "{component.value}" not found in Block "{block.block.name}"')

            code_component = block.components[component.value]
            if not isinstance(code_component, list):
                raise RuntimeError(f'Block component "{component.value}" is not a list')
            code += translate(code_component, parsing_items, translation, indent=indentation + block_translation.inner_indent)

        elif component.component_type == StructureComponentType.Whitespace:
            code += component.value
        else:
            raise RuntimeError(f'Unknown structure component type "{component.component_type}"')

    return code


def translate_typename(typename: TypenameInstance, translation: TranslationItems) -> str:
    if typename.value.name not in translation.primitive_types:
        raise RuntimeError(f'Primitive type "{typename.value.name}" not found in translation items')
    return translation.primitive_types[typename.value.name].translate


def translate_structured_object(so: StructuredObjectInstance, parsing_items: ParsingItems, translation: TranslationItems, indentation: int) -> str:
    if so.so.name not in translation.structured_objects:
        raise RuntimeError(f'Keyword "{so.so.name}" not found in translation items')
    keyword_translation = translation.structured_objects[so.so.name]

    code = ""

    for component in keyword_translation.translate:
        if component.component_type == StructureComponentType.String:
            code += component.value
        elif component.component_type == StructureComponentType.Variable:
            if component.value not in so.components:
                raise RuntimeError(f'Variable "{component.value}" not found in component "{so.so.name}"')

            code_component = so.components[component.value]
            if isinstance(code_component, ValueToken):
                code += translate_value_token(code_component, translation)
            elif isinstance(code_component, OperatorInstance):
                code += translate_operator_instance(code_component, translation)
            elif isinstance(code_component, StructuredObjectInstance):
                code += translate_structured_object(code_component, parsing_items, translation, indentation)
            elif isinstance(code_component, BlockInstance):
                code += translate_block(code_component, parsing_items, translation, indentation)
            elif isinstance(code_component, TypenameInstance):
                code += translate_typename(code_component, translation)
            elif isinstance(code_component, NameInstance):
                code += code_component.value
            else:
                raise RuntimeError(f'Unknown component type "{type(code_component)}"')

        elif component.component_type == StructureComponentType.Whitespace:
            code += component.value
        else:
            raise RuntimeError(f'Unknown structure component type "{component.component_type}"')

    return code


def translate(ast: list, parsing_items: ParsingItems, translation: TranslationItems, indent=0) -> str:
    code = " "*indent
    for item in ast:
        if isinstance(item, StructuredObjectInstance):
            code += translate_structured_object(item, parsing_items, translation, indent)
            code += translation.expression_separators['main'].value
        elif isinstance(item, OperatorInstance):
            code += translate_operator_instance(item, translation)
            code += translation.expression_separators['main'].value
        elif isinstance(item, ValueToken):
            code += translate_value_token(item, translation)
            code += translation.expression_separators['main'].value
        else:
            raise RuntimeError(f'Unexpected AST item: {item}')
        if translation.expression_separators['main'].value == '\n':
            code += " "*indent
    return code
