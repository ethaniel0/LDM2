from dataclasses import dataclass
from ldm.ast.parsing_types import ExpressionToken, ParsingItems, MakeVariableInstance
from ldm.translation.translation_types import (MakeVariableTranslation,
                                               StructureComponentType,
                                               PrimitiveTypeTranslation,
                                               ValueKeywordTranslation,
                                               parse_translate_into_components)



@dataclass
class TranslationItems:
    make_variables: dict[str, MakeVariableTranslation]
    primitive_types: dict[str, PrimitiveTypeTranslation]
    value_keywords: dict[str, ValueKeywordTranslation]
    expression_separator: str

    def __init__(self, specs: dict):
        self.make_variables = {}
        self.primitive_types = {}
        self.value_keywords = {}
        self.expression_separator = None

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
                if self.expression_separator != None:
                    raise AttributeError("expression separator defined more than once")
                self.expression_separator = item['translate']
        
        if not self.expression_separator:
            self.expression_separator = '' 


def translate_type(name: str, translation_items: TranslationItems):
    if name not in translation_items.primitive_types:
        raise RuntimeError(f'Primitive type "{name}" not found in translation items')
    return translation_items.primitive_types[name].translate


def matches_type(expression_type, necessary_type, parsing_items: ParsingItems):
    if expression_type == necessary_type:
        return True
    # check for downstream "is" relationship
    types = parsing_items.config_spec.primitive_types
    if expression_type not in types:
        raise RuntimeError(f'Primitive type "{expression_type}" not found in spec')
    if necessary_type not in types:
        raise RuntimeError(f'Primitive type "{necessary_type}" not found in spec')

    val = types[necessary_type]
    while val.superclass != '':
        if val.superclass == expression_type:
            return True
        val = types[val.superclass]

    return False


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
                t: ExpressionToken = mv.structure[var_name]
                if not matches_type(t.var_type, mv.typename.value, parsing_items):
                    raise RuntimeError(f'Variable "{var_name}" type mismatch: {t.var_type} != {mv.typename.value}')
                code += mv.structure[var_name].value

    return code


def translate(ast: list, parsing_items: ParsingItems, translation: TranslationItems) -> str:
    code = ""
    for item in ast:
        if isinstance(item, MakeVariableInstance):
            code += translate_make_variable(item, parsing_items, translation)
            code += translation.expression_separator
        else:
            raise RuntimeError(f'Unexpected AST item: {item}')
    return code
