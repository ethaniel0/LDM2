import sys
sys.path.append('..')
import unittest
import json
from ldm.lib_config2.spec_parsing import parse_spec
from ldm.lib_config2.def_parsing import add_structure_definitions_to_spec
from ldm.source_tokenizer.tokenizer_types import *
from ldm.ast.parsing import ParsingItems, parse
from ldm.ast import parsing_types as ast_pt
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
        source_code = "-"
        tokens = TOKENIZER.tokenize(source_code)
        # even if unknown, will recognize as operator
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.Operator
        assert tokens[0].value == "-"
        assert tokens[0].line == 1

    def test_make_variable_parsing(self):
        source_code = "int x = 5"
        tokens = TOKENIZER.tokenize(source_code)
        ast = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.MakeVariableInstance)
        mv: ast_pt.MakeVariableInstance = ast[0]
        assert mv.name == 'standard'
        assert mv.structure['typename'].value == 'int'
        assert mv.typename.value == 'int'
        assert mv.structure['varname'].value == 'x'
        assert mv.varname.value == 'x'

        expr: ast_pt.ValueToken = mv.structure['expr']
        assert isinstance(expr, ast_pt.ValueToken)
        assert expr.value.value == '5'
        var_expr: ast_pt.ValueToken = mv.expr
        assert var_expr.value.value == '5'

    def test_make_variable_with_simple_operator(self):
        source_code = "int x = 5 + 4"
        tokens = TOKENIZER.tokenize(source_code)
        ast = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.MakeVariableInstance)
        mv: ast_pt.MakeVariableInstance = ast[0]
        assert mv.name == 'standard'
        assert mv.structure['typename'].value == 'int'
        assert mv.typename.value == 'int'
        assert mv.structure['varname'].value == 'x'
        assert mv.varname.value == 'x'

        expr: ast_pt.ValueToken = mv.structure['expr']
        assert isinstance(expr, ast_pt.OperatorInstance)
        assert expr.operator.name == '+'
        assert len(expr.operands) == 2
        assert isinstance(expr.operands[0], ast_pt.ValueToken)
        assert isinstance(expr.operands[1], ast_pt.ValueToken)
        assert expr.operands[0].value.value == '5'
        assert expr.operands[1].value.value == '4'

    def test_make_variable_with_multiple_operator(self):
        source_code = "int x = 5 + 4 * 6"
        tokens = TOKENIZER.tokenize(source_code)
        ast = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.MakeVariableInstance)
        mv: ast_pt.MakeVariableInstance = ast[0]
        assert mv.name == 'standard'
        assert mv.structure['typename'].value == 'int'

        expr: ast_pt.ValueToken = mv.structure['expr']
        assert isinstance(expr, ast_pt.OperatorInstance)
        assert expr.operator.name == '+'
        assert len(expr.operands) == 2
        assert isinstance(expr.operands[0], ast_pt.ValueToken)
        assert isinstance(expr.operands[1], ast_pt.OperatorInstance)
        assert expr.operands[0].value.value == '5'

        inner_op: ast_pt.OperatorInstance = expr.operands[1]
        assert inner_op.operator.name == '*'
        assert len(inner_op.operands) == 2
        assert isinstance(inner_op.operands[0], ast_pt.ValueToken)
        assert isinstance(inner_op.operands[1], ast_pt.ValueToken)
        assert inner_op.operands[0].value.value == '4'
        assert inner_op.operands[1].value.value == '6'

        source_code = "int x = 5 * 4 + 6"
        tokens = TOKENIZER.tokenize(source_code)
        ast = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.MakeVariableInstance)
        mv: ast_pt.MakeVariableInstance = ast[0]
        assert mv.name == 'standard'
        assert mv.structure['typename'].value == 'int'

        expr: ast_pt.ValueToken = mv.structure['expr']
        assert isinstance(expr, ast_pt.OperatorInstance)
        assert expr.operator.name == '+'
        assert len(expr.operands) == 2
        assert isinstance(expr.operands[0], ast_pt.OperatorInstance)
        assert isinstance(expr.operands[1], ast_pt.ValueToken)
        assert expr.operands[1].value.value == '6'

        inner_op: ast_pt.OperatorInstance = expr.operands[0]
        assert inner_op.operator.name == '*'
        assert len(inner_op.operands) == 2
        assert isinstance(inner_op.operands[0], ast_pt.ValueToken)
        assert isinstance(inner_op.operands[1], ast_pt.ValueToken)
        assert inner_op.operands[0].value.value == '5'
        assert inner_op.operands[1].value.value == '4'

    def test_make_variable_with_minus_and_negation(self):
        source_code = "int x = 5 - -8"
        tokens = TOKENIZER.tokenize(source_code)
        ast = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.MakeVariableInstance)
        mv: ast_pt.MakeVariableInstance = ast[0]
        assert mv.name == 'standard'

        expr: ast_pt.ValueToken = mv.structure['expr']
        assert isinstance(expr, ast_pt.OperatorInstance)
        assert expr.operator.name == '-'
        assert len(expr.operands) == 2
        assert isinstance(expr.operands[0], ast_pt.ValueToken)
        assert isinstance(expr.operands[1], ast_pt.OperatorInstance)
        assert expr.operands[0].value.value == '5'

        inner_op: ast_pt.OperatorInstance = expr.operands[1]
        assert inner_op.operator.name == '- neg'
        assert len(inner_op.operands) == 1
        assert isinstance(inner_op.operands[0], ast_pt.ValueToken)
        assert inner_op.operands[0].value.value == '8'

    def test_make_variable_with_ternary_operator(self):
        source_code = "int x = 5 > 3 ? 1 : 0"
        tokens = TOKENIZER.tokenize(source_code)
        ast = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.MakeVariableInstance)
        mv: ast_pt.MakeVariableInstance = ast[0]
        assert mv.name == 'standard'

        expr: ast_pt.ValueToken = mv.structure['expr']
        assert isinstance(expr, ast_pt.OperatorInstance)
        assert expr.operator.name == '?:'
        assert len(expr.operands) == 3
        assert isinstance(expr.operands[0], ast_pt.OperatorInstance)
        assert isinstance(expr.operands[1], ast_pt.ValueToken)
        assert isinstance(expr.operands[2], ast_pt.ValueToken)
        assert expr.operands[1].value.value == '1'
        assert expr.operands[2].value.value == '0'

        inner_op: ast_pt.OperatorInstance = expr.operands[0]
        assert inner_op.operator.name == '>'
        assert len(inner_op.operands) == 2
        assert isinstance(inner_op.operands[0], ast_pt.ValueToken)
        assert isinstance(inner_op.operands[1], ast_pt.ValueToken)
        assert inner_op.operands[0].value.value == '5'
        assert inner_op.operands[1].value.value == '3'

    def test_parsing(self):
        spec = load_setup()
        source_code = "int x = 5"
        tokens = TOKENIZER.tokenize(source_code)
        ast = parse(tokens, ParsingItems(spec), TOKENIZER_ITEMS)


if __name__ == '__main__':
    unittest.main()
