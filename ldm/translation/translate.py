from dataclasses import dataclass
from typing import Any

from ldm.lib_config2.parsing_types import Spec, \
    StructureSpecComponent, ComponentType
from ldm.ast.parsing_types import (ParsingItems,
                                   ValueToken,
                                   TypeSpec,
                                   StructuredObjectInstance,
                                   TypenameInstance, SOInstanceItem)
from ldm.translation.translation_types import (TranslationStructureComponentType,
                                               TranslationStructureComponent,
                                               parse_translate_into_components,
                                               ParameterizedTranslation, DirectStringTranslation)

def parse_component_structure(arg: dict, spec_components: dict[str, StructureSpecComponent]) -> list[TranslationStructureComponent]:
    structure = arg['translate']
    components = parse_translate_into_components(structure)

    for component in components:
        if component.component_type != TranslationStructureComponentType.Variable:
            continue

        if component.value.startswith('.'):
            continue

        try:
            comp_type = spec_components[component.value].base
        except KeyError as ke:
            raise ke
        if comp_type == ComponentType.REPEATED_ELEMENT:
            if 'component_features' not in arg:
                raise ValueError(f"Repeated element {component.value} must have component structures in structure {arg['name']}")
            if component.value not in arg['component_features']:
                raise ValueError(f"Repeated element {component.value} not found in component structures")
            comp_defs = arg['component_features'][component.value]
            if not component.inner_fields:
                component.inner_fields = {}
            component.inner_structure = parse_component_structure(
                comp_defs,
                spec_components[component.value].other['components']
            )
            component.inner_fields['separator'] = comp_defs['separator']

        elif comp_type == ComponentType.EXPRESSIONS:
            if 'component_features' not in arg or component.value not in arg['component_features']:
                continue
            arg_comp = arg['component_features'][component.value]
            if not component.inner_fields:
                component.inner_fields = {}
            if 'indent' in arg_comp:
                component.inner_fields['indent'] = arg_comp['indent']

    return components


@dataclass
class TranslationItems:
    structured_objects: dict[str, ParameterizedTranslation]
    primitive_types: dict[str, DirectStringTranslation]
    value_keywords: dict[str, DirectStringTranslation]
    expression_separators: dict[str, DirectStringTranslation]
    created_types = dict[str, ParameterizedTranslation]

    def __init__(self, translate_specs: dict, parse_spec: Spec):
        self.structured_objects: dict[str, ParameterizedTranslation] = {}
        self.primitive_types: dict[str, DirectStringTranslation] = {}
        self.value_keywords: dict[str, DirectStringTranslation] = {}
        self.expression_separators: dict[str, DirectStringTranslation] = {}
        self.created_types: dict[str, ParameterizedTranslation] = {}

        for item in translate_specs:
            if 'type' not in item:
                raise RuntimeError('Translation item missing "type" field')
            if 'name' not in item:
                raise RuntimeError('Translation item missing "name" field')

            if item['type']  == 'structure':
                parse_spec_item = parse_spec.structured_objects[item['name']]
                components = parse_component_structure(
                    item,
                    parse_spec_item.structure.component_specs,
                )

                self.structured_objects[item['name']] = ParameterizedTranslation(item['type'],
                                                                                    item['name'],
                                                                                    components)
            elif item['type'] == 'primitive_type':
                self.primitive_types[item['name']] = DirectStringTranslation(item['type'],
                                                                              item['name'],
                                                                              item['translate'])
            elif item['type'] == 'created_type':
                parse_spec_item = parse_spec.structured_objects[item['name']]
                components = parse_component_structure(
                    item,
                    parse_spec_item.structure.component_specs,
                )

                self.created_types[item['name']] = ParameterizedTranslation(item['type'],
                                                                          item['name'],
                                                                          components)

            elif item['type'] == 'value_keyword':
                self.value_keywords[item['name']] = DirectStringTranslation(item['type'],
                                                                            item['name'],
                                                                            item['translate'])
            elif item['type'] == 'expression_separator':
                self.expression_separators[item['name']] = DirectStringTranslation(item['type'],
                                                                                   item['name'],
                                                                                   item['translate'])

            # else:
            #     raise RuntimeError(f"Unknown translation item type {item['type']}")
        
        if len(self.expression_separators) == 0:
            self.expression_separators['main'] = DirectStringTranslation('expression_separator', 'main', '')


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

def translate_typename(typename: TypenameInstance, translation: TranslationItems) -> str:
    tn: TypeSpec = typename.value
    if tn.name in translation.primitive_types:
        return translation.primitive_types[tn.name].translate

    if not tn.associated_structure:
        raise RuntimeError(f'Type "{tn.name}" has no associated structure')

    if tn.associated_structure.name not in translation.created_types:
        raise RuntimeError(f'Associated structure of {tn.associated_structure.name} for type {tn.name} does not have a translation')

    so = translation.created_types[tn.associated_structure.name]

    code = ""

    for component in so.translate:
        if component.component_type == TranslationStructureComponentType.String:
            code += component.value
        elif component.component_type == TranslationStructureComponentType.Variable:
            if component.value[0] != '.':
                raise RuntimeError('Created type translate variable must start with a . to signify fields from typename')

            result = tn.extract_from_path(component.value[1:])

            if not isinstance(result, str):
                raise RuntimeError('Created type translate variable must end in a name component')

            code += result

        elif component.component_type == TranslationStructureComponentType.Whitespace:
            code += component.value
        else:
            raise RuntimeError(f'Unknown structure component type "{component.component_type}"')

    return code

def translate_expressions(exprs: list, translation_component: TranslationStructureComponent, translation: TranslationItems, indentation: int) -> str:
    code = ""

    if 'indent' in translation_component.inner_fields:
        inner_indent = translation_component.inner_fields['indent']
    else:
        inner_indent = 0

    if not isinstance(exprs, list):
        raise RuntimeError(f'Expressions component "{exprs}" is not a list')
    code += translate(exprs, translation, indent=indentation + inner_indent)

    return code

def translate_component(component: SOInstanceItem | ValueToken | StructuredObjectInstance, translation_component: TranslationStructureComponent, translation: TranslationItems, indentation: int) -> str:
    if isinstance(component, ValueToken):
        return translate_value_token(component, translation)
    elif isinstance(component, StructuredObjectInstance):
        return translate_structured_object(component, translation, indentation)

    comp_item_type = component.item_type
    comp_value: Any = component.value
    code = ""

    if comp_item_type == ComponentType.EXPRESSION:
        if isinstance(component.value, ValueToken):
            code += translate_value_token(comp_value, translation)
        elif isinstance(comp_value, StructuredObjectInstance):
            code += translate_structured_object(comp_value, translation, indentation)
        else:
            raise RuntimeError('expression has value other than value or operator')
    elif comp_item_type == ComponentType.TYPENAME:
        typename_code = translate_typename(component, translation)
        code += typename_code
    elif comp_item_type == ComponentType.NAME:
        code += component.value
    elif comp_item_type == ComponentType.REPEATED_ELEMENT:
        code += translate_repeated_element(comp_value, translation_component, translation, indentation)
    elif comp_item_type == ComponentType.EXPRESSIONS:
        code += translate_expressions(component.value, translation_component, translation, indentation)
    elif comp_item_type == ComponentType.STRUCTURE:
        soi: StructuredObjectInstance = component.value
        code += translate_structured_object(soi, translation, indentation)

    else:
        raise RuntimeError(f'Unknown component type "{type(component)}"')

    return code


def translate_structured_object(so: StructuredObjectInstance, translation: TranslationItems, indentation: int) -> str:
    if so.so.name not in translation.structured_objects:
        raise RuntimeError(f'Keyword "{so.so.name}" not found in translation items')
    so_translation = translation.structured_objects[so.so.name]

    code = ""

    for component in so_translation.translate:
        if component.component_type == TranslationStructureComponentType.String:
            code += component.value
        elif component.component_type == TranslationStructureComponentType.Variable:
            if component.value not in so.components:
                raise RuntimeError(f'Variable "{component.value}" not found in component "{so.so.name}"')

            code += translate_component(so.components[component.value], component, translation, indentation)

        elif component.component_type == TranslationStructureComponentType.Whitespace:
            code += component.value
        else:
            raise RuntimeError(f'Unknown structure component type "{component.component_type}"')

    return code


def translate_repeated_element(elements: list[StructuredObjectInstance], component: TranslationStructureComponent, translation: TranslationItems, indent: int) -> str:
    comp_defs = component.inner_structure

    code = ""

    for i, element in enumerate(elements):
        for comp_def in comp_defs:
            if comp_def.component_type == TranslationStructureComponentType.String:
                code += comp_def.value
            elif comp_def.component_type == TranslationStructureComponentType.Whitespace:
                code += comp_def.value

            elif comp_def.component_type == TranslationStructureComponentType.Variable:
                if comp_def.value not in element.components:
                    raise RuntimeError(f'Variable "{comp_def.value}" not found in repeated element')
                code_component = element.components[comp_def.value]
                code += translate_component(code_component, comp_def, translation, indent)

        if i < len(elements) - 1:
            code += component.inner_fields['separator']

    return code


def translate(ast: list, translation: TranslationItems, indent=0) -> str:
    code = " "*indent
    for item in ast:
        if isinstance(item, StructuredObjectInstance):
            code += translate_structured_object(item, translation, indent)
            code += translation.expression_separators['main'].translate
        elif isinstance(item, ValueToken):
            code += translate_value_token(item, translation)
            code += translation.expression_separators['main'].translate
        else:
            raise RuntimeError(f'Unexpected AST item: {item}')
        if translation.expression_separators['main'].translate == '\n':
            code += " "*indent
    return code
