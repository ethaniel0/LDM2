import sys

from ldm.errors.LDMError import ParsingTracebackError

sys.path.append('..')

from ldm.ast.parsing_types import StructuredObjectInstance


import unittest
import json
from ldm.lib_config2.spec_parsing import parse_spec
from ldm.lib_config2.def_parsing import add_structure_definitions_to_spec
from ldm.source_tokenizer.tokenizer_types import *
from ldm.ast.parsing import ParsingItems, parse
from ldm.ast import parsing_types as ast_pt
import ldm.lib_config2.parsing_types as pt
from parse_test_spec_definitions import SPEC, TOKENIZER, TOKENIZER_ITEMS


def load_setup():
    spec_file = 'test_std_spec.json'
    def_file = 'test_std_def.json'
    with open(spec_file) as f:
        spec_data = json.load(f)
        spec = parse_spec(spec_data)

    with open(def_file) as f:
        def_data = json.load(f)
        add_structure_definitions_to_spec(spec, def_data)

    return spec


class MyTestCase(unittest.TestCase):
    
    def test_literal_tokenizing(self):
        source_code = "hello"
        tokens = TOKENIZER.tokenize(source_code)

        assert len(tokens) == 1
        assert tokens[0].type == TokenType.Identifier
        assert tokens[0].value == "hello"
        assert tokens[0].line == 1

    def test_number_tokenizing(self):
        source_code = "123 1.5 2"
        tokens = TOKENIZER.tokenize(source_code)

        assert len(tokens) == 3
        assert tokens[0].type == TokenType.Integer
        assert tokens[0].value == "123"
        assert tokens[0].line == 1

        assert tokens[1].type == TokenType.Float
        assert tokens[1].value == "1.5"
        assert tokens[1].line == 1

        assert tokens[2].type == TokenType.Integer
        assert tokens[2].value == "2"
        assert tokens[2].line == 1

    def test_operator_tokenizing(self):
        source_code = "+"
        tokens = TOKENIZER.tokenize(source_code)

        assert len(tokens) == 1
        assert tokens[0].type == TokenType.Operator
        assert tokens[0].value == "+"
        assert tokens[0].line == 1

    def test_unknown_operator(self):
        source_code = "&"
        tokens = TOKENIZER.tokenize(source_code)
        # even if unknown, will recognize as operator
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.Operator
        assert tokens[0].value == "&"
        assert tokens[0].line == 1

    def test_make_variable_parsing(self):
        source_code = "int x = 5"
        tokens = TOKENIZER.tokenize(source_code)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'
        assert isinstance(mv.components['type'], ast_pt.TypenameInstance)
        assert mv.components['type'].value.name == 'int'
        assert mv.components['varname'].value == 'x'

        expr = mv.components['expr']
        assert isinstance(expr, ast_pt.ValueToken)
        assert expr.value.value == '5'
        assert expr.var_type.name == 'int'

    def test_make_variable_with_simple_operator(self):
        source_code = "int x = 5 + 4"
        tokens = TOKENIZER.tokenize(source_code)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'
        assert mv.components['type'].value.name == 'int'
        assert mv.components['varname'].value == 'x'

        expr = mv.components['expr']
        assert isinstance(expr, ast_pt.StructuredObjectInstance)
        assert expr.so.name == '+'
        assert expr.operator_fields.result_type.name == 'int'
        assert len(expr.components) == 2
        assert isinstance(expr.components['left'], ast_pt.ValueToken)
        assert isinstance(expr.components['right'], ast_pt.ValueToken)
        assert expr.components['left'].value.value == '5'
        assert expr.components['right'].value.value == '4'

    def test_make_variable_with_multiple_operator(self):
        source_code = "int x = 5 + 4 * 6.5"
        tokens = TOKENIZER.tokenize(source_code)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'
        assert mv.components['type'].value.name == 'int'

        expr = mv.components['expr']
        assert isinstance(expr, ast_pt.StructuredObjectInstance)
        assert expr.so.name == '+'
        assert expr.operator_fields.result_type.name == 'float'
        assert len(expr.components) == 2
        assert isinstance(expr.components['left'], ast_pt.ValueToken)
        assert isinstance(expr.components['right'], ast_pt.StructuredObjectInstance)
        assert expr.components['left'].value.value == '5'
        assert expr.operator_fields.result_type.name == 'float'

        inner_op: ast_pt.StructuredObjectInstance = expr.components['right']
        assert inner_op.so.name == '*'
        assert len(inner_op.components) == 2
        assert isinstance(inner_op.components['left'], ast_pt.ValueToken)
        assert isinstance(inner_op.components['right'], ast_pt.ValueToken)
        assert inner_op.components['left'].value.value == '4'
        assert inner_op.components['right'].value.value == '6.5'

        source_code = "int x = 5 * 4 + 6"
        tokens = TOKENIZER.tokenize(source_code)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'
        assert mv.components['type'].value.name == 'int'

        expr = mv.components['expr']
        assert isinstance(expr, ast_pt.StructuredObjectInstance)
        assert expr.so.name == '+'
        assert len(expr.components) == 2
        assert isinstance(expr.components['left'], ast_pt.StructuredObjectInstance)
        assert isinstance(expr.components['right'], ast_pt.ValueToken)
        assert expr.components['right'].value.value == '6'

        inner_op: ast_pt.StructuredObjectInstance = expr.components['left']
        assert inner_op.so.name == '*'
        assert len(inner_op.components) == 2
        assert isinstance(inner_op.components['left'], ast_pt.ValueToken)
        assert isinstance(inner_op.components['right'], ast_pt.ValueToken)
        assert inner_op.components['left'].value.value == '5'
        assert inner_op.components['right'].value.value == '4'

    def test_make_variable_with_two_same_precedence_operators_ltr(self):
        source_code = "int x = 5 + 4 + 6"
        tokens = TOKENIZER.tokenize(source_code)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'

        expr = mv.components['expr']
        assert isinstance(expr, ast_pt.StructuredObjectInstance)
        assert expr.so.name == '+'
        assert len(expr.components) == 2
        assert isinstance(expr.components['left'], ast_pt.StructuredObjectInstance)
        assert isinstance(expr.components['right'], ast_pt.ValueToken)
        assert expr.components['right'].value.value == '6'

        inner_op: ast_pt.StructuredObjectInstance = expr.components['left']
        assert inner_op.so.name == '+'
        assert len(inner_op.components) == 2
        assert isinstance(inner_op.components['left'], ast_pt.ValueToken)
        assert isinstance(inner_op.components['right'], ast_pt.ValueToken)
        assert inner_op.components['left'].value.value == '5'
        assert inner_op.components['right'].value.value == '4'

    def test_make_variable_with_two_same_precedence_operators_rtl(self):
        source_code = "int x = 5 ++ 4 ++ 6"
        tokens = TOKENIZER.tokenize(source_code)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'

        expr: ast_pt.ValueToken = mv.components['expr']
        assert isinstance(expr, ast_pt.StructuredObjectInstance)
        assert expr.so.name == '++'
        assert len(expr.components) == 2
        assert isinstance(expr.components['left'], ast_pt.ValueToken)
        assert isinstance(expr.components['right'], ast_pt.StructuredObjectInstance)
        assert expr.components['left'].value.value == '5'

        inner_op: ast_pt.StructuredObjectInstance = expr.components['right']
        assert inner_op.so.name == '++'
        assert len(inner_op.components) == 2
        assert isinstance(inner_op.components['left'], ast_pt.ValueToken)
        assert isinstance(inner_op.components['right'], ast_pt.ValueToken)
        assert inner_op.components['left'].value.value == '4'
        assert inner_op.components['right'].value.value == '6'

    def test_make_variable_with_minus_and_negation(self):
        source_code = "int x = 5 - -8"
        tokens = TOKENIZER.tokenize(source_code)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'

        expr = mv.components['expr']
        assert isinstance(expr, ast_pt.StructuredObjectInstance)
        assert expr.so.name == '-'
        assert len(expr.components) == 2
        assert isinstance(expr.components['left'], ast_pt.ValueToken)
        assert isinstance(expr.components['right'], ast_pt.StructuredObjectInstance)
        assert expr.components['left'].value.value == '5'

        inner_op: ast_pt.StructuredObjectInstance = expr.components['right']
        assert inner_op.so.name == '- neg'
        assert len(inner_op.components) == 1
        assert isinstance(inner_op.components['right'], ast_pt.ValueToken)
        assert inner_op.components['right'].value.value == '8'

    def test_make_variable_with_ternary_operator(self):
        source_code = "int x = 5 > 3 ? 1 : 0"
        tokens = TOKENIZER.tokenize(source_code)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'

        expr= mv.components['expr']
        assert isinstance(expr, ast_pt.StructuredObjectInstance)
        assert expr.so.name == '?:'
        assert expr.operator_fields.result_type.name == 'int'
        assert len(expr.components) == 3
        assert isinstance(expr.components['condition'], ast_pt.StructuredObjectInstance)
        assert isinstance(expr.components['on_true'], ast_pt.ValueToken)
        assert isinstance(expr.components['on_false'], ast_pt.ValueToken)
        assert expr.components['on_true'].value.value == '1'
        assert expr.components['on_false'].value.value == '0'

        inner_op: ast_pt.StructuredObjectInstance = expr.components['condition']
        assert inner_op.so.name == '>'
        assert inner_op.operator_fields.result_type.name == 'bool'
        assert len(inner_op.components) == 2
        assert isinstance(inner_op.components['left'], ast_pt.ValueToken)
        assert isinstance(inner_op.components['right'], ast_pt.ValueToken)
        assert inner_op.components['left'].value.value == '5'
        assert inner_op.components['right'].value.value == '3'

    def test_make_variable_with_weird_plus_operator(self):
        weird_op = pt.StructuredObject(
            name="weird +",
            structure=pt.Structure(
                component_specs={
                    "x1": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION, name="x1", other={}),
                    "x2": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION, name="x2", other={}),
                    "x3": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION, name="x3", other={}),
                    "x4": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION, name="x4", other={})
                },
                component_defs=[
                    pt.StructureComponent(
                        component_type=pt.StructureComponentType.Variable,
                        value="x1"
                    ),
                    pt.StructureComponent(
                        component_type=pt.StructureComponentType.String,
                        value="+"
                    ),
                    pt.StructureComponent(
                        component_type=pt.StructureComponentType.Variable,
                        value="x2"
                    ),
                    pt.StructureComponent(
                        component_type=pt.StructureComponentType.String,
                        value="?"
                    ),
                    pt.StructureComponent(
                        component_type=pt.StructureComponentType.Variable,
                        value="x3"
                    ),
                    pt.StructureComponent(
                        component_type=pt.StructureComponentType.String,
                        value="@"
                    ),
                    pt.StructureComponent(
                        component_type=pt.StructureComponentType.Variable,
                        value="x4"
                    ),
                    pt.StructureComponent(
                        component_type=pt.StructureComponentType.String,
                        value="$"
                    )
                ]
            ),
            create_operator=pt.CreateOperator(
                fields=["x1", "x2", "x3", "x4"],
                precedence=16,
                associativity=pt.Associativity.LEFT_TO_RIGHT,
                overloads=[
                    pt.OperatorOverload(
                        name="weird +",
                        return_type=pt.TypeSpec('int', 0, []),
                        variables={
                            "x1": pt.TypeSpec('int', 0, []),
                            "x2": pt.TypeSpec('int', 0, []),
                            "x3": pt.TypeSpec('int', 0, []),
                            "x4": pt.TypeSpec('int', 0, [])
                        }
                    ),
                ]
            )
        )

        SPEC.structured_objects['weird +'] = weird_op

        source_code = "int x = 5 + 2 ? 3 @ 4 $ + 5"
        tokens = TOKENIZER.tokenize(source_code)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        del SPEC.structured_objects['weird +']

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'

        expr: ast_pt.ValueToken = mv.components['expr']
        assert isinstance(expr, ast_pt.StructuredObjectInstance)
        assert expr.so.name == '+'
        assert len(expr.components) == 2

        inner_op: ast_pt.StructuredObjectInstance = expr.components['left']
        assert inner_op.so.name == 'weird +'
        assert inner_op.operator_fields.result_type.name == 'int'
        assert len(inner_op.components) == 4
        assert isinstance(inner_op.components['x1'], ast_pt.ValueToken)
        assert isinstance(inner_op.components['x2'], ast_pt.ValueToken)
        assert isinstance(inner_op.components['x3'], ast_pt.ValueToken)
        assert isinstance(inner_op.components['x3'], ast_pt.ValueToken)
        assert inner_op.components['x1'].value.value == '5'
        assert inner_op.components['x2'].value.value == '2'
        assert inner_op.components['x3'].value.value == '3'
        assert inner_op.components['x4'].value.value == '4'

        assert expr.components['right'].value.value == '5'

    def test_with_parentheses(self):
        source_code = "int x = (5 + 4) * 6"
        tokens = TOKENIZER.tokenize(source_code)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'

        expr: ast_pt.ValueToken = mv.components['expr']

        assert isinstance(expr, ast_pt.StructuredObjectInstance)
        assert expr.so.name == '*'
        assert len(expr.components) == 2
        assert isinstance(expr.components['left'], ast_pt.StructuredObjectInstance)
        assert isinstance(expr.components['right'], ast_pt.ValueToken)

        inner_op: ast_pt.StructuredObjectInstance = expr.components['left']
        assert inner_op.so.name == '()'
        assert len(inner_op.components) == 1
        assert isinstance(inner_op.components['inside'], ast_pt.StructuredObjectInstance)
        assert inner_op.components['inside'].so.name == '+'
        assert len(inner_op.components['inside'].components) == 2
        assert isinstance(inner_op.components['inside'].components['left'], ast_pt.ValueToken)
        assert isinstance(inner_op.components['inside'].components['right'], ast_pt.ValueToken)
        assert inner_op.components['inside'].components['left'].value.value == '5'
        assert inner_op.components['inside'].components['right'].value.value == '4'

    def test_multiline(self):
        source = '''
        int x = 5 + 4.5;
        int y = 6 * 3;
        '''
        tokens = TOKENIZER.tokenize(source)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 2
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        assert isinstance(ast[1], ast_pt.StructuredObjectInstance)

        mv1: ast_pt.StructuredObjectInstance = ast[0]
        mv2: ast_pt.StructuredObjectInstance = ast[1]

        assert mv1.so.name == 'make_variable_standard'
        assert mv2.so.name == 'make_variable_standard'

        assert mv1.components['type'].value.name == 'int'
        assert mv2.components['type'].value.name == 'int'

        assert mv1.components['varname'].value == 'x'
        assert mv2.components['varname'].value == 'y'

        assert mv1.components['expr'].so.name == '+'
        assert mv2.components['expr'].so.name == '*'

        assert mv1.components['expr'].operator_fields.result_type.name == 'float'
        assert mv1.components['expr'].components['left'].value.value == '5'
        assert mv1.components['expr'].components['right'].value.value == '4.5'

        assert mv2.components['expr'].operator_fields.result_type.name == 'int'
        assert mv2.components['expr'].components['left'].value.value == '6'
        assert mv2.components['expr'].components['right'].value.value == '3'

    def test_multiline_fails_when_no_expression_separators(self):
        source = '''
                int x = 5 + 4
                int y = 6 * 3
                '''
        tokens = TOKENIZER.tokenize(source)
        try:
            parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)
            assert False
        except ParsingTracebackError as e:
            assert True

        source = '''
                int x = 5 + 4
                x = x - 8
                '''
        tokens = TOKENIZER.tokenize(source)
        try:
            parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)
            assert False
        except ParsingTracebackError as e:
            print(e)
            assert True

    def test_if_empty(self):
        source = '''
        if (true){
        
        }
        '''
        tokens = TOKENIZER.tokenize(source)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        assert ast[0].so.name == 'if'

        if_body = ast[0].components['body']
        assert isinstance(if_body.value, StructuredObjectInstance)
        assert len(if_body.value.components) == 1
        if_body_body = if_body.value.components['body'].value
        assert len(if_body_body) == 0

    def test_if_not_empty(self):
        source = '''
        if (true){
            int x = 5 + 4;
        }
        '''
        tokens = TOKENIZER.tokenize(source)
        ast, _ = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        assert ast[0].so.name == 'if'

        if_body = ast[0].components['body']
        assert isinstance(if_body.value, StructuredObjectInstance)
        assert len(if_body.value.components) == 1
        if_body_body = if_body.value.components['body'].value
        assert len(if_body_body) == 1
        assert isinstance(if_body_body[0], ast_pt.StructuredObjectInstance)

    def test_if_and_func_with_load_setup(self):
        spec = load_setup()
        source_code = """
        int p = 14;
        if (p < 12){
            int x = 5 + 4;
        }
        
        float func(int a, bool b){
            int x = 9;
            x = x + 3;
        }
        """
        tokens = TOKENIZER.tokenize(source_code)

        ast, context = parse(tokens, ParsingItems(spec), TOKENIZER_ITEMS)

        assert len(ast) == 3
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        assert isinstance(ast[1], ast_pt.StructuredObjectInstance)

        mv: ast_pt.StructuredObjectInstance = ast[0]
        assert mv.so.name == 'make_variable_standard'
        assert mv.components['type'].value.name == 'int'
        assert mv.components['varname'].value == 'p'
        assert mv.components['expr'].value.value == '14'

        if_inst: ast_pt.StructuredObjectInstance = ast[1]
        assert if_inst.so.name == 'if'
        assert len(if_inst.components) == 2
        assert isinstance(if_inst.components['condition'], ast_pt.StructuredObjectInstance)
        assert if_inst.components['body'].item_type == ast_pt.ComponentType.STRUCTURE
        assert isinstance(if_inst.components['body'].value, StructuredObjectInstance)
        if_body: ast_pt.SOInstanceItem = if_inst.components['body'].value.components['body']
        assert isinstance(if_body.value, list)
        assert len(if_body.value) == 1
        assert isinstance(if_body.value[0], ast_pt.StructuredObjectInstance)
        assert if_body.value[0].so.name == 'make_variable_standard'

        func: ast_pt.StructuredObjectInstance = ast[2]
        assert func.so.name == 'function'
        assert func.components['type'].value.name == 'float'
        assert func.components['varname'].value == 'func'
        assert isinstance(func.components['body'].value, StructuredObjectInstance)
        assert len(func.components['body'].value.components) == 1
        assert isinstance(func.components['body'].value.components['body'], ast_pt.SOInstanceItem)
        func_body: ast_pt.SOInstanceItem = func.components['body'].value.components['body']
        assert isinstance(func_body.value, list)
        assert len(func_body.value) == 2
        assert isinstance(func_body.value[0], ast_pt.StructuredObjectInstance)
        assert func_body.value[0].so.name == 'make_variable_standard'
        assert isinstance(func_body.value[1], ast_pt.StructuredObjectInstance)

        assert len(func.components['arguments'].value) == 2
        arguments = func.components['arguments'].value
        assert arguments[0].components['type'].value.name == 'int'
        assert arguments[0].components['varname'].value == 'a'
        assert arguments[1].components['type'].value.name == 'bool'
        assert arguments[1].components['varname'].value == 'b'

    def test_function_and_function_call(self):
        spec = load_setup()
        source_code = """
        int translate(int x, bool y){
            int k = x + 8;
            y ? x : k + 1;
        }

        translate(5, true);
        """
        tokens = TOKENIZER.tokenize(source_code)

        ast, context = parse(tokens, ParsingItems(spec), TOKENIZER_ITEMS)

        assert len(ast) == 2
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)
        assert isinstance(ast[1], ast_pt.StructuredObjectInstance)

        func: ast_pt.StructuredObjectInstance = ast[0]
        assert func.so.name == 'function'
        assert func.components['type'].value.name == 'int'
        assert func.components['varname'].value == 'translate'
        assert len(func.components['arguments'].value) == 2
        args = func.components['arguments'].value
        assert args[0].components['type'].value.name == 'int'
        assert args[0].components['varname'].value == 'x'
        assert args[1].components['type'].value.name == 'bool'
        assert args[1].components['varname'].value == 'y'
        assert isinstance(func.components['body'].value, StructuredObjectInstance)
        assert len(func.components['body'].value.components) == 1
        body = func.components['body'].value.components['body'].value
        assert len(body) == 2
        assert isinstance(body[0], ast_pt.StructuredObjectInstance)
        assert isinstance(body[1], ast_pt.StructuredObjectInstance)
        assert body[0].so.name == 'make_variable_standard'
        assert body[1].so.name == '+'

        func_call: ast_pt.StructuredObjectInstance = ast[1]
        assert func_call.so.name == 'function_call'
        assert func_call.components['function_name'].value.value == 'translate'
        assert len(func_call.components['arguments'].value) == 2
        arg1 = func_call.components['arguments'].value[0]
        arg2 = func_call.components['arguments'].value[1]
        assert isinstance(arg1, ast_pt.StructuredObjectInstance)
        assert isinstance(arg2, ast_pt.StructuredObjectInstance)

        assert arg1.components['arg'].value.value == '5'
        assert arg2.components['arg'].value.value == 'true'

    def test_create_type(self):
        spec = load_setup()
        source_code = """
        struct Point {
            int x;
            int y;
        }
        
        Point p = Point {x=6, y=7};
        
        int x = p.x;
        """
        tokens = TOKENIZER.tokenize(source_code)

        ast, context = parse(tokens, ParsingItems(spec), TOKENIZER_ITEMS)

        assert len(ast) == 3
        assert isinstance(ast[0], ast_pt.StructuredObjectInstance)

if __name__ == '__main__':
    unittest.main()
